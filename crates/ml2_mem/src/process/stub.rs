//! Non-Windows stub for the Spelunky 2 process reader. Every entry
//! point returns `Unsupported` so the crate still builds cross-platform;
//! callers should gate any live-attach path on the target OS.

use crate::error::{MemError, Result};
use crate::process::ReadProcess;

pub const FEEDCODE_MARKER: &[u8] = &[0x00, 0xde, 0xc0, 0xed, 0xfe];
pub const SPEL2_EXE_NAME: &str = "Spel2.exe";

/// Placeholder that never yields a valid process. Constructing one
/// unconditionally errors; every method surfaces `Unsupported`.
pub struct Spel2Process {
    _private: (),
}

impl Spel2Process {
    pub fn from_pid(_pid: u32) -> Result<Self> {
        Err(MemError::Unsupported)
    }

    pub fn attach() -> Result<Self> {
        Err(MemError::Unsupported)
    }

    pub fn get_feedcode(&self) -> Result<u64> {
        Err(MemError::Unsupported)
    }
}

impl ReadProcess for Spel2Process {
    fn read_bytes(&self, _addr: u64, _dst: &mut [u8]) -> Result<()> {
        Err(MemError::Unsupported)
    }
}

pub fn find_spelunky2_pid() -> Option<u32> {
    None
}
