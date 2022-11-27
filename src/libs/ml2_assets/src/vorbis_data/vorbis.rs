use thiserror::Error;
use vorbis_sys::{
    vorbis_comment, vorbis_comment_clear, vorbis_commentheader_out, vorbis_info, vorbis_info_clear,
};

use super::ogg::OggPacket;

#[derive(Error, Debug)]
pub enum VorbisError {
    #[error("Unimplemented mode; unable to comply with bitrate request.")]
    Unimplemented,

    #[error("Packet data submitted to vorbis_synthesis is not audio data.")]
    NotAudio,

    #[error("Invalid packet submitted to vorbis_synthesis.")]
    BadPacket,

    #[error("Bitstream/page/packet is not Vorbis data.")]
    NotVorbis,

    #[error("Invalid Vorbis bitstream header.")]
    BadHeader,

    #[error("Internal logic fault; indicates a bug or heap/stack corruption.")]
    Fault,

    #[error("Unknown Error {0}")]
    Unknown(i32),
}

pub(crate) struct VorbisInfo(vorbis_info);

impl VorbisInfo {
    pub(crate) fn new() -> Self {
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

pub(crate) struct VorbisComment(vorbis_comment);

impl VorbisComment {
    pub(crate) fn new() -> Self {
        Self(unsafe {
            let mut comment = std::mem::MaybeUninit::uninit();
            vorbis_sys::vorbis_comment_init(comment.as_mut_ptr());
            comment.assume_init()
        })
    }

    pub(crate) fn header_out(&mut self, packet: &mut OggPacket) -> Result<(), VorbisError> {
        match unsafe { vorbis_commentheader_out(&mut self.0, &mut packet.0) } {
            0 => Ok(()),
            vorbis_sys::OV_EIMPL => Err(VorbisError::Unimplemented),
            err => Err(VorbisError::Unknown(err)),
        }
    }
}

impl Drop for VorbisComment {
    fn drop(&mut self) {
        unsafe {
            vorbis_comment_clear(&mut self.0);
        }
    }
}

pub(crate) fn vorbis_synthesis_header_in(
    info: &mut VorbisInfo,
    comment: &mut VorbisComment,
    packet: &mut OggPacket,
) -> Result<(), VorbisError> {
    match unsafe {
        vorbis_sys::vorbis_synthesis_headerin(&mut info.0, &mut comment.0, &mut packet.0)
    } {
        0 => Ok(()),
        vorbis_sys::OV_ENOTVORBIS => Err(VorbisError::NotVorbis),
        vorbis_sys::OV_EBADHEADER => Err(VorbisError::BadHeader),
        vorbis_sys::OV_EFAULT => Err(VorbisError::Fault),
        err => Err(VorbisError::Unknown(err)),
    }
}

pub(crate) fn vorbis_packet_blocksize(
    info: &mut VorbisInfo,
    packet: &mut OggPacket,
) -> Result<i32, VorbisError> {
    match unsafe { vorbis_sys::vorbis_packet_blocksize(&mut info.0, &mut packet.0) } {
        vorbis_sys::OV_ENOTAUDIO => Err(VorbisError::NotAudio),
        vorbis_sys::OV_EBADPACKET => Err(VorbisError::BadPacket),
        err if err <= 0 => Err(VorbisError::Unknown(err)),
        blocksize => Ok(blocksize),
    }
}
