//! `PolyPointer<Base>`: a pointer that reads a shared base type at the
//! target address and delegates concrete-variant decoding to the caller.
//!
//! Spelunky 2 entities are polymorphic: `Entity*` points at some derived
//! class (Player, Enemy, Item, ...) and callers pick the concrete type
//! from a discriminant field (usually `Entity::type` or the vtable
//! pointer at offset 0).
//!
//! `PolyPointer<B>` reads and stores the pointer address; callers who
//! need a concrete subtype call `.load_as::<Concrete>(process)` or write
//! a resolver that inspects `B`'s type field and dispatches.
//!
//! Distinct from `Pointer<T>` because entities need base-type access
//! (for type dispatch) without paying to fully decode a specific
//! concrete subtype at every field read.

use crate::error::{MemError, Result};
use crate::mem_type::{MemLayout, MemType};
use crate::process::{self, ReadProcess};

#[derive(Debug, Clone, Copy)]
pub struct PolyPointer<Base> {
    pub addr: u64,
    _phantom: std::marker::PhantomData<Base>,
}

impl<Base> PolyPointer<Base> {
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

impl<Base: MemType> PolyPointer<Base> {
    /// Reads the base type at the target address. None on null, the
    /// value otherwise. Callers use this to look at the discriminant
    /// field before deciding which concrete subtype to decode.
    pub fn load_base(&self, process: &dyn ReadProcess) -> Result<Option<Base>> {
        if self.is_null() {
            return Ok(None);
        }
        Ok(Some(Base::read_from(process, self.addr)?))
    }
}

impl<Base> PolyPointer<Base> {
    /// Reads a different concrete type at the same target address.
    /// Consumers dispatch to the right `Concrete` after inspecting the
    /// base's discriminant field. Null yields `Ok(None)`.
    pub fn load_as<Concrete: MemType>(
        &self,
        process: &dyn ReadProcess,
    ) -> Result<Option<Concrete>> {
        if self.is_null() {
            return Ok(None);
        }
        Ok(Some(Concrete::read_from(process, self.addr)?))
    }

    /// Same as `load_as` but treats null as an error.
    pub fn load_as_required<Concrete: MemType>(
        &self,
        process: &dyn ReadProcess,
    ) -> Result<Concrete> {
        if self.is_null() {
            return Err(MemError::NullPointer { addr: self.addr });
        }
        Concrete::read_from(process, self.addr)
    }
}

impl<Base> MemType for PolyPointer<Base> {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self::from_addr(process::read_u64(process, addr)?))
    }
}

impl<Base> MemLayout for PolyPointer<Base> {
    const SIZE: usize = std::mem::size_of::<u64>();
}
