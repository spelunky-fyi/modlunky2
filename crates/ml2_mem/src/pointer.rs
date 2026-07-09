//! `Pointer<T>`: a stored 8-byte address that dereferences to a value
//! of type `T` when asked. Useful for game-state fields that point at
//! another struct (e.g. `Inventory*`).
//!
//! Reading the pointer itself yields the raw address only. Callers who
//! want the pointed-at value call `.load(process)` which handles the
//! null check and defers to `T::read_from(process, addr)`.

use crate::error::{MemError, Result};
use crate::mem_type::{MemLayout, MemType};
use crate::process::{self, ReadProcess};

#[derive(Debug, Clone, Copy)]
pub struct Pointer<T> {
    pub addr: u64,
    _phantom: std::marker::PhantomData<T>,
}

impl<T> Pointer<T> {
    pub fn from_addr(addr: u64) -> Self {
        Self {
            addr,
            _phantom: std::marker::PhantomData,
        }
    }

    pub fn is_null(&self) -> bool {
        self.addr == 0
    }
}

impl<T: MemType> Pointer<T> {
    /// Follow the pointer. Returns `Ok(None)` when the stored address is
    /// zero (null); returns the read result otherwise. Distinguishes
    /// null from a read failure so callers can render "not present" vs
    /// "read error" differently.
    pub fn load(&self, process: &dyn ReadProcess) -> Result<Option<T>> {
        if self.is_null() {
            return Ok(None);
        }
        Ok(Some(T::read_from(process, self.addr)?))
    }

    /// Same as `load` but treats null as an error. Use in fields where
    /// null indicates a bug or torn read rather than a valid absence.
    pub fn load_required(&self, process: &dyn ReadProcess) -> Result<T> {
        if self.is_null() {
            return Err(MemError::NullPointer { addr: self.addr });
        }
        T::read_from(process, self.addr)
    }
}

impl<T> MemType for Pointer<T> {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self::from_addr(process::read_u64(process, addr)?))
    }
}

impl<T> MemLayout for Pointer<T> {
    const SIZE: usize = std::mem::size_of::<u64>();
}
