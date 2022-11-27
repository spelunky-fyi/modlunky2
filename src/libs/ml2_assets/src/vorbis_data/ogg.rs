use ogg_sys::{
    ogg_packet, ogg_packet_clear, ogg_page, ogg_stream_clear, ogg_stream_flush,
    ogg_stream_packetin, ogg_stream_pageout, ogg_stream_state, oggpack_buffer, oggpack_bytes,
    oggpack_write, oggpack_writecheck, oggpack_writeclear,
};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum OggError {
    #[error("Initialization of {0} failed.")]
    InitializationFailed(String),

    #[error("An internal error occurred on {0}")]
    InternalError(String),

    #[error("Buffer is not ready or encountered an error.")]
    NotReady,
}

pub(crate) struct OggStreamState(ogg_stream_state);

impl OggStreamState {
    pub(crate) fn new(serialno: i32) -> Result<Self, OggError> {
        Ok(Self(unsafe {
            let mut state = std::mem::MaybeUninit::uninit();
            let result = ogg_sys::ogg_stream_init(state.as_mut_ptr(), serialno);
            if result == -1 {
                return Err(OggError::InitializationFailed("OggStream".into()));
            }
            state.assume_init()
        }))
    }

    pub(crate) fn packetin(&mut self, packet: &mut OggPacket) -> Result<(), OggError> {
        unsafe {
            let result = ogg_stream_packetin(&mut self.0, &mut packet.0);
            if result == -1 {
                return Err(OggError::InternalError("ogg_stream_packetin".into()));
            }
        }
        Ok(())
    }

    pub(crate) fn pageout(&mut self, page: &mut OggPage) -> i32 {
        unsafe { ogg_stream_pageout(&mut self.0, &mut page.0) }
    }

    pub(crate) fn write_packets_pageout(&mut self, buf: &mut Vec<u8>) {
        let mut page = OggPage::new();
        while self.pageout(&mut page) > 0 {
            buf.extend_from_slice(page.header());
            buf.extend_from_slice(page.body());
        }
    }

    pub(crate) fn flush(&mut self, page: &mut OggPage) -> i32 {
        unsafe { ogg_stream_flush(&mut self.0, &mut page.0) }
    }

    pub(crate) fn write_packets_flush(&mut self, buf: &mut Vec<u8>) {
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

pub(crate) struct OggpackBuffer(oggpack_buffer);

impl OggpackBuffer {
    pub(crate) fn new() -> Self {
        Self(unsafe {
            let mut buffer = std::mem::MaybeUninit::uninit();
            ogg_sys::oggpack_writeinit(buffer.as_mut_ptr());
            buffer.assume_init()
        })
    }

    pub(crate) fn write(&mut self, value: u32, bits: i32) {
        unsafe {
            oggpack_write(&mut self.0, value, bits);
        }
    }

    pub(crate) fn writecheck(&mut self) -> Result<i32, OggError> {
        Ok(unsafe {
            let result = oggpack_writecheck(&mut self.0);
            if result != 0 {
                return Err(OggError::NotReady);
            }
            result
        })
    }

    pub(crate) fn bytes(&mut self) -> i32 {
        unsafe { oggpack_bytes(&mut self.0) }
    }

    pub(crate) fn buffer(&mut self) -> &[u8] {
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

pub(crate) struct OggPage(ogg_page);

impl OggPage {
    pub(crate) fn new() -> Self {
        Self(unsafe { std::mem::MaybeUninit::zeroed().assume_init() })
    }

    pub(crate) fn header_len(&self) -> i32 {
        self.0.header_len
    }

    pub(crate) fn header(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.0.header, self.header_len() as usize) }
    }

    pub(crate) fn body_len(&self) -> i32 {
        self.0.body_len
    }

    pub(crate) fn body(&self) -> &[u8] {
        unsafe { std::slice::from_raw_parts(self.0.body, self.body_len() as usize) }
    }
}

pub(crate) struct OggPacket(pub(crate) ogg_packet);

impl OggPacket {
    pub(crate) fn new() -> Self {
        Self(unsafe { std::mem::MaybeUninit::zeroed().assume_init() })
    }

    pub(crate) fn clear(&mut self) {
        unsafe { ogg_packet_clear(&mut self.0) }
    }
}

impl Drop for OggPacket {
    fn drop(&mut self) {
        self.clear();
    }
}
