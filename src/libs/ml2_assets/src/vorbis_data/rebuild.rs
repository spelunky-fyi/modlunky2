use std::io::Cursor;
use std::io::Read;

use byteorder::ReadBytesExt;
use byteorder::LE;
use thiserror::Error;

use ml2_vorbis_header::LOOKUP as VORBIS_HEADER_LOOKUP;

use crate::fsb5::{SampleMetadataType, SampleMetadataValue, Track};
use crate::vorbis_data::ogg::OggPacket;
use crate::vorbis_data::ogg::OggStreamState;
use crate::vorbis_data::ogg::OggpackBuffer;
use crate::vorbis_data::vorbis::vorbis_packet_blocksize;
use crate::vorbis_data::vorbis::vorbis_synthesis_header_in;
use crate::vorbis_data::vorbis::VorbisComment;
use crate::vorbis_data::vorbis::VorbisInfo;

use super::ogg::OggError;
use super::vorbis::VorbisError;

#[derive(Error, Debug)]
pub enum RebuildError {
    #[error("OggError")]
    OggError(#[from] OggError),

    #[error("VorbisError")]
    VorbisError(#[from] VorbisError),

    #[error("IoError")]
    IoError(#[from] std::io::Error),
}

fn rebuild_id_header(
    channels: u8,
    frequency: u32,
    blocksize_short: u32,
    blocksize_long: u32,
) -> Result<OggPacket, RebuildError> {
    let mut packet = OggPacket::new();

    let mut buffer = OggpackBuffer::new();

    buffer.write(0x01, 8);
    for c in b"vorbis" {
        buffer.write(*c as u32, 8);
    }
    buffer.write(0, 32);
    buffer.write(channels as u32, 8);
    buffer.write(frequency, 32);
    buffer.write(0, 32);
    buffer.write(0, 32);
    buffer.write(0, 32);
    buffer.write(u32::BITS - blocksize_short.leading_zeros() - 1, 4);
    buffer.write(u32::BITS - blocksize_long.leading_zeros() - 1, 4);
    buffer.write(1, 1);

    buffer.writecheck()?;

    packet.0.bytes = buffer.bytes();

    let mut mem = Vec::with_capacity(packet.0.bytes as usize);
    mem.extend_from_slice(buffer.buffer());
    let mem = Box::leak(mem.into_boxed_slice());
    packet.0.packet = mem.as_mut_ptr();

    packet.0.b_o_s = 1;
    packet.0.e_o_s = 0;
    packet.0.granulepos = 0;
    packet.0.packetno = 0;

    Ok(packet)
}

fn rebuild_comment_header() -> Result<OggPacket, RebuildError> {
    let mut packet = OggPacket::new();
    let mut comment = VorbisComment::new();
    comment.header_out(&mut packet)?;

    Ok(packet)
}

fn rebuild_setup_header(setup_packet_buff: &[u8]) -> OggPacket {
    let mut packet = OggPacket::new();

    let mut mem = Vec::with_capacity(setup_packet_buff.len());
    mem.extend_from_slice(setup_packet_buff);
    let mem = Box::leak(mem.into_boxed_slice());

    packet.0.packet = mem.as_mut_ptr();
    packet.0.bytes = setup_packet_buff.len() as i32;
    packet.0.b_o_s = 0;
    packet.0.e_o_s = 0;
    packet.0.granulepos = 0;
    packet.0.packetno = 2;

    packet
}

pub(crate) fn rebuild_vorbis(track: &Track) -> Result<Vec<u8>, RebuildError> {
    let crc32 = match track.metadata.get(&SampleMetadataType::VorbisData) {
        Some(SampleMetadataValue::VorbisData { crc32, .. }) => *crc32,
        _ => panic!("Missing expected metadata"),
    };

    let setup_packet_buff = match VORBIS_HEADER_LOOKUP.get(&crc32) {
        Some(val) => *val,
        _ => panic!("Unknown Vorbis Header: {crc32}"),
    };

    let mut info = VorbisInfo::new();
    let mut comment = VorbisComment::new();
    let mut state = OggStreamState::new(1)?;

    let mut id_header = rebuild_id_header(track.channels, track.frequency, 0x100, 0x800)?;
    let mut comment_header = rebuild_comment_header()?;
    let mut setup_header = rebuild_setup_header(setup_packet_buff);

    vorbis_synthesis_header_in(&mut info, &mut comment, &mut id_header)?;
    vorbis_synthesis_header_in(&mut info, &mut comment, &mut comment_header)?;
    vorbis_synthesis_header_in(&mut info, &mut comment, &mut setup_header)?;

    let mut out = Vec::new();

    state.packetin(&mut id_header)?;
    state.write_packets_pageout(&mut out);
    state.packetin(&mut comment_header)?;
    state.write_packets_pageout(&mut out);
    state.packetin(&mut setup_header)?;
    state.write_packets_pageout(&mut out);
    state.write_packets_flush(&mut out);

    let mut packetno = setup_header.0.packetno;
    let mut granulepos = 0;
    let mut prev_blocksize = 0;

    let mut inbuf = Cursor::new(&track.data);
    let mut packet_size = inbuf.read_u16::<LE>()?;
    while packet_size > 0 {
        packetno += 1;

        let mut packet = OggPacket::new();

        let mut mem = vec![0; packet_size as usize];
        inbuf.read_exact(&mut mem)?;
        let mem = Box::leak(mem.into_boxed_slice());

        packet.0.packet = mem.as_mut_ptr();
        packet.0.bytes = packet_size as i32;
        packet.0.packetno = packetno;

        match inbuf.read_u16::<LE>() {
            Ok(size) => packet_size = size,
            Err(_) => packet_size = 0,
        };
        packet.0.e_o_s = match packet_size {
            0 => 1,
            _ => 0,
        };

        let blocksize = vorbis_packet_blocksize(&mut info, &mut packet)?;

        granulepos = match prev_blocksize {
            0 => 0,
            size => granulepos + (blocksize + size) / 4,
        };
        packet.0.granulepos = granulepos as i64;
        prev_blocksize = blocksize;

        state.packetin(&mut packet)?;
        state.write_packets_pageout(&mut out);
    }
    state.write_packets_flush(&mut out);

    Ok(out)
}
