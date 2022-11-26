use std::io::Cursor;
use std::io::Read;

use byteorder::ReadBytesExt;
use byteorder::LE;
use ogg_sys::{
    ogg_packet, ogg_page, ogg_stream_clear, ogg_stream_flush, ogg_stream_packetin,
    ogg_stream_pageout, ogg_stream_state, oggpack_buffer, oggpack_bytes, oggpack_write,
    oggpack_writecheck, oggpack_writeclear,
};
use vorbis_sys::{
    vorbis_comment, vorbis_comment_clear, vorbis_commentheader_out, vorbis_info, vorbis_info_clear,
};

use ml2_vorbis_header::LOOKUP as VORBIS_HEADER_LOOKUP;

use crate::soundbank::{SampleMetadataType, SampleMetadataValue, Track};

struct VorbisInfo(vorbis_info);

impl VorbisInfo {
    fn new() -> Self {
        Self(unsafe {
            let mut info = std::mem::MaybeUninit::uninit();
            vorbis_sys::vorbis_info_init(info.as_mut_ptr());
            info.assume_init()
        })
    }
}

impl Drop for VorbisInfo {
    fn drop(&mut self) {
        unsafe {
            vorbis_info_clear(&mut self.0);
        };
    }
}

struct VorbisComment(vorbis_comment);

impl VorbisComment {
    fn new() -> Self {
        Self(unsafe {
            let mut comment = std::mem::MaybeUninit::uninit();
            vorbis_sys::vorbis_comment_init(comment.as_mut_ptr());
            comment.assume_init()
        })
    }

    fn header_out(&mut self, packet: &mut ogg_packet) -> i32 {
        unsafe { vorbis_commentheader_out(&mut self.0, packet) }
    }
}

impl Drop for VorbisComment {
    fn drop(&mut self) {
        unsafe {
            vorbis_comment_clear(&mut self.0);
        }
    }
}

struct OggStreamState(ogg_stream_state);

impl OggStreamState {
    fn new(serialno: i32) -> Self {
        Self(unsafe {
            let mut state = std::mem::MaybeUninit::uninit();
            ogg_sys::ogg_stream_init(state.as_mut_ptr(), serialno);
            state.assume_init()
        })
    }

    fn packetin(&mut self, packet: &mut ogg_packet) -> i32 {
        unsafe { ogg_stream_packetin(&mut self.0, packet) }
    }

    fn pageout(&mut self, page: &mut OggPage) -> i32 {
        unsafe { ogg_stream_pageout(&mut self.0, &mut page.0) }
    }

    fn write_packets_pageout(&mut self, buf: &mut Vec<u8>) {
        let mut page = OggPage::new();
        while self.pageout(&mut page) > 0 {
            buf.extend_from_slice(page.header());
            buf.extend_from_slice(page.body());
        }
    }

    fn flush(&mut self, page: &mut OggPage) -> i32 {
        unsafe { ogg_stream_flush(&mut self.0, &mut page.0) }
    }

    fn write_packets_flush(&mut self, buf: &mut Vec<u8>) {
        let mut page = OggPage::new();
        while self.flush(&mut page) > 0 {
            buf.extend_from_slice(page.header());
            buf.extend_from_slice(page.body());
        }
    }
}

impl Drop for OggStreamState {
    fn drop(&mut self) {
        unsafe {
            ogg_stream_clear(&mut self.0);
        }
    }
}

struct OggpackBuffer(oggpack_buffer);

impl OggpackBuffer {
    fn new() -> Self {
        Self(unsafe {
            let mut buffer = std::mem::MaybeUninit::uninit();
            ogg_sys::oggpack_writeinit(buffer.as_mut_ptr());
            buffer.assume_init()
        })
    }

    fn write(&mut self, value: u32, bits: i32) -> i32 {
        unsafe { oggpack_write(&mut self.0, value, bits) }
    }

    fn writecheck(&mut self) -> i32 {
        unsafe { oggpack_writecheck(&mut self.0) }
    }

    fn bytes(&mut self) -> i32 {
        unsafe { oggpack_bytes(&mut self.0) }
    }

    fn buffer(&mut self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.0.buffer, self.bytes() as usize) }
    }
}

impl Drop for OggpackBuffer {
    fn drop(&mut self) {
        unsafe {
            oggpack_writeclear(&mut self.0);
        };
    }
}

struct OggPage(ogg_page);

impl OggPage {
    fn new() -> Self {
        Self(unsafe { std::mem::MaybeUninit::zeroed().assume_init() })
    }

    fn header_len(&self) -> i32 {
        self.0.header_len
    }

    fn header(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.0.header, self.header_len() as usize) }
    }

    fn body_len(&self) -> i32 {
        self.0.header_len
    }

    fn body(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.0.body, self.body_len() as usize) }
    }
}

fn vorbis_synthesis_header_in(
    info: &mut VorbisInfo,
    comment: &mut VorbisComment,
    packet: &mut ogg_packet,
) -> i32 {
    unsafe { vorbis_sys::vorbis_synthesis_headerin(&mut info.0, &mut comment.0, packet) }
}

fn rebuild_id_header(
    channels: u8,
    frequency: u32,
    blocksize_short: u32,
    blocksize_long: u32,
) -> ogg_sys::ogg_packet {
    let mut packet: ogg_sys::ogg_packet = unsafe { std::mem::MaybeUninit::zeroed().assume_init() };

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

    buffer.writecheck();

    packet.bytes = buffer.bytes();

    let mut mem = Vec::with_capacity(packet.bytes as usize);
    mem.extend_from_slice(buffer.buffer());
    let mem = Box::leak(mem.into_boxed_slice());
    packet.packet = mem.as_mut_ptr();

    packet.b_o_s = 1;
    packet.e_o_s = 0;
    packet.granulepos = 0;
    packet.packetno = 0;

    packet
}

fn rebuild_comment_header() -> ogg_sys::ogg_packet {
    let mut packet: ogg_sys::ogg_packet = unsafe { std::mem::MaybeUninit::zeroed().assume_init() };
    let mut comment = VorbisComment::new();
    comment.header_out(&mut packet);

    packet
}

fn rebuild_setup_header(setup_packet_buff: &[u8]) -> ogg_sys::ogg_packet {
    let mut packet: ogg_sys::ogg_packet = unsafe { std::mem::MaybeUninit::zeroed().assume_init() };

    let mut mem = Vec::with_capacity(setup_packet_buff.len());
    mem.extend_from_slice(setup_packet_buff);
    let mem = Box::leak(mem.into_boxed_slice());

    packet.packet = mem.as_mut_ptr();
    packet.bytes = setup_packet_buff.len() as i32;
    packet.b_o_s = 0;
    packet.e_o_s = 0;
    packet.granulepos = 0;
    packet.packetno = 2;

    packet
}

pub(crate) fn rebuild_vorbis(track: &Track) -> Vec<u8> {
    let crc32 = match track.metadata.get(&SampleMetadataType::VorbisData) {
        Some(SampleMetadataValue::VorbisData { crc32, .. }) => *crc32,
        _ => panic!("Missing expected metadata"),
    };

    let setup_packet_buff = match VORBIS_HEADER_LOOKUP.get(&crc32) {
        Some(val) => *val,
        _ => panic!("Unknown Vorbis Header."),
    };

    let mut info = VorbisInfo::new();
    let mut comment = VorbisComment::new();
    let mut state = OggStreamState::new(1);

    let mut id_header = rebuild_id_header(track.channels, track.frequency, 0x100, 0x800);
    let mut comment_header = rebuild_comment_header();
    let mut setup_header = rebuild_setup_header(setup_packet_buff);

    vorbis_synthesis_header_in(&mut info, &mut comment, &mut id_header);
    vorbis_synthesis_header_in(&mut info, &mut comment, &mut comment_header);
    vorbis_synthesis_header_in(&mut info, &mut comment, &mut setup_header);

    let mut out = Vec::new();

    state.packetin(&mut id_header);
    state.write_packets_pageout(&mut out);
    state.packetin(&mut comment_header);
    state.write_packets_pageout(&mut out);
    state.packetin(&mut setup_header);
    state.write_packets_pageout(&mut out);
    state.write_packets_flush(&mut out);

    let mut packetno = setup_header.packetno;
    let mut granulepos = 0;
    let mut prev_blocksize = 0;

    let mut inbuf = Cursor::new(&track.data);
    let mut packet_size = inbuf.read_u16::<LE>().unwrap();
    while packet_size > 0 {
        packetno += 1;

        let mut packet: ogg_sys::ogg_packet =
            unsafe { std::mem::MaybeUninit::zeroed().assume_init() };

        let mut mem = vec![0; packet_size as usize];
        inbuf.read_exact(&mut mem).unwrap();
        let mem = Box::leak(mem.into_boxed_slice());

        packet.packet = mem.as_mut_ptr();
        packet.bytes = packet_size as i32;
        packet.packetno = packetno;

        match inbuf.read_u16::<LE>() {
            Ok(size) => {
                packet_size = size;
                packet.e_o_s = 0;
            }
            Err(_) => {
                packet_size = 0;
                packet.e_o_s = 1;
            }
        };

        let blocksize = unsafe { vorbis_sys::vorbis_packet_blocksize(&mut info.0, &mut packet) };
        assert!(blocksize > 0);

        granulepos = match prev_blocksize {
            0 => 0,
            size => granulepos + (blocksize + size) / 4,
        };
        packet.granulepos = granulepos as i64;
        prev_blocksize = blocksize;

        state.packetin(&mut packet);
        state.write_packets_pageout(&mut out);
    }

    out
}
