//! MSVC `std::vector<T>` reader.
//!
//! Layout on 64-bit MSVC is three pointers:
//!
//! ```text
//! struct vector {
//!     T*  first;       // 0x00, base of the buffer
//!     T*  last;        // 0x08, one past the last live element
//!     T*  capacity;    // 0x10, one past the allocation
//! };
//! ```
//!
//! Length in elements is `(last - first) / size_of::<T>()`; capacity is
//! unused here and stored only so struct offsets past the vector line up.
//!
//! `Vector<T>` reads the three pointers eagerly (24 bytes). Call
//! `.load(process)` to walk the elements, cheap when you only need the
//! length, expensive when you need the whole buffer.

use crate::error::{MemError, Result};
use crate::mem_type::{MemLayout, MemType};
use crate::process::{self, ReadProcess};

const VECTOR_SIZE: usize = 24;

#[derive(Debug, Clone, Copy)]
pub struct Vector<T> {
    pub first: u64,
    pub last: u64,
    pub capacity: u64,
    _phantom: std::marker::PhantomData<T>,
}

impl<T> Vector<T> {
    /// Length in elements when `T`'s in-process size is known. Kept
    /// generic over stride so callers reading a T without MemLayout can
    /// still fall back to a raw byte length via `len_bytes()`.
    pub fn len_bytes(&self) -> u64 {
        self.last.saturating_sub(self.first)
    }

    pub fn is_null(&self) -> bool {
        self.first == 0
    }
}

impl<T: MemLayout> Vector<T> {
    /// Element count. Zero when the vector is null or empty. Uses
    /// integer division; a partial trailing element would indicate a
    /// torn read (impossible in practice on a paused/live game frame).
    pub fn len(&self) -> usize {
        let stride = T::SIZE as u64;
        if stride == 0 {
            return 0;
        }
        (self.len_bytes() / stride) as usize
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

impl<T: MemType + MemLayout> Vector<T> {
    /// Reads every element. Convenient for small vectors; hot paths
    /// walking huge vectors should call `at()` per element instead.
    pub fn load(&self, process: &dyn ReadProcess) -> Result<Vec<T>> {
        if self.is_null() {
            return Ok(Vec::new());
        }
        let stride = T::SIZE as u64;
        if stride == 0 {
            return Err(MemError::Read {
                addr: self.first,
                msg: "zero-sized element type".into(),
            });
        }
        let n = self.len();
        let mut out = Vec::with_capacity(n);
        for i in 0..n {
            out.push(T::read_from(process, self.first + i as u64 * stride)?);
        }
        Ok(out)
    }

    /// Reads the element at `index`. Panics on out-of-bounds so callers
    /// pair it with `len()` bounds checks. Cheaper than `load()` when
    /// you only need one entry.
    pub fn at(&self, process: &dyn ReadProcess, index: usize) -> Result<T> {
        let n = self.len();
        if index >= n {
            return Err(MemError::Read {
                addr: self.first,
                msg: format!("vector index {index} out of bounds ({n})"),
            });
        }
        let stride = T::SIZE as u64;
        T::read_from(process, self.first + index as u64 * stride)
    }
}

impl<T> MemType for Vector<T> {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self {
            first: process::read_u64(process, addr)?,
            last: process::read_u64(process, addr + 8)?,
            capacity: process::read_u64(process, addr + 16)?,
            _phantom: std::marker::PhantomData,
        })
    }
}

impl<T> MemLayout for Vector<T> {
    const SIZE: usize = VECTOR_SIZE;
}
