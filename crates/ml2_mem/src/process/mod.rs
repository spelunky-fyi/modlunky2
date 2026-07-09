//! Low-level "read raw bytes from a process address" abstraction.
//!
//! `ReadProcess` is the seam between the type system (MemType /
//! MemStruct decode) and the OS-specific mechanism for getting bytes out
//! of a process (Windows' ReadProcessMemory, tests' in-memory buffer,
//! future macOS / Linux / debugger backends).

#[cfg(windows)]
mod win;
#[cfg(windows)]
pub use win::{FEEDCODE_MARKER, SPEL2_EXE_NAME, Spel2Process, find_spelunky2_pid};

#[cfg(not(windows))]
mod stub;
#[cfg(not(windows))]
pub use stub::{FEEDCODE_MARKER, SPEL2_EXE_NAME, Spel2Process, find_spelunky2_pid};

use crate::error::{MemError, Result};

/// Something that can hand back N bytes at a given virtual address in a
/// target process's memory space. Object-safe on purpose: the derive
/// macro passes `&dyn ReadProcess` to every field read, and higher-level
/// types (Pointer, Vector, UnorderedMap) all operate through this trait.
pub trait ReadProcess {
    /// Reads `dst.len()` bytes starting at `addr` into `dst`. Errors on
    /// short reads, protected pages, or a detached process.
    fn read_bytes(&self, addr: u64, dst: &mut [u8]) -> Result<()>;
}

/// Convenience helpers layered over `read_bytes` for the numeric
/// primitives that show up all over game-state decode. Kept as free
/// functions so callers use `read_u32(process, addr)` rather than
/// spelling out a mutable buffer at every call site.
macro_rules! read_prim {
    ($fn:ident, $ty:ty) => {
        pub fn $fn(process: &dyn ReadProcess, addr: u64) -> Result<$ty> {
            let mut buf = [0u8; std::mem::size_of::<$ty>()];
            process.read_bytes(addr, &mut buf)?;
            Ok(<$ty>::from_le_bytes(buf))
        }
    };
}

read_prim!(read_u8, u8);
read_prim!(read_u16, u16);
read_prim!(read_u32, u32);
read_prim!(read_u64, u64);
read_prim!(read_i8, i8);
read_prim!(read_i16, i16);
read_prim!(read_i32, i32);
read_prim!(read_i64, i64);
read_prim!(read_f32, f32);
read_prim!(read_f64, f64);

/// Reads a `bool` stored as one byte. Non-zero maps to true. Matches
/// how MSVC lays out `bool`.
pub fn read_bool(process: &dyn ReadProcess, addr: u64) -> Result<bool> {
    Ok(read_u8(process, addr)? != 0)
}

/// Fixed-length in-memory buffer used for unit tests. Behaves like a
/// process rooted at address 0; the buffer is the entire address space.
/// Doesn't allocate anything at runtime; hands back a reference-shaped
/// error on out-of-range reads.
pub struct MockProcess<'a> {
    pub data: &'a [u8],
}

impl<'a> ReadProcess for MockProcess<'a> {
    fn read_bytes(&self, addr: u64, dst: &mut [u8]) -> Result<()> {
        let start = addr as usize;
        let end = start.checked_add(dst.len()).ok_or_else(|| MemError::Read {
            addr,
            msg: "address overflow".into(),
        })?;
        if end > self.data.len() {
            return Err(MemError::Read {
                addr,
                msg: format!("out of bounds: need {end} bytes, have {}", self.data.len()),
            });
        }
        dst.copy_from_slice(&self.data[start..end]);
        Ok(())
    }
}
