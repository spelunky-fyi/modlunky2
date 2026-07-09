//! The three traits every game-state field goes through:
//!
//! - `MemType`: anything readable from a process address.
//! - `MemLayout`: anything with a compile-time size in the target
//!   address space; needed by array / vector readers so they know how
//!   far to stride between elements.
//! - `MemStruct`: offset-mapped record types produced by
//!   `#[derive(MemStruct)]`. Every `MemStruct` also implements `MemType`
//!   automatically (the derive covers that).

use crate::error::Result;
use crate::process::{self, ReadProcess};

pub trait MemType: Sized {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self>;
}

/// Compile-time size of a `MemType` in the target process. Array +
/// vector readers use this to compute the stride between elements. The
/// derive macro will also emit this for structs so nested struct arrays
/// stride correctly; until then hand-written structs must implement it.
pub trait MemLayout {
    const SIZE: usize;
}

/// Layout-mapped struct. `MemStruct::read_from(process, base)` reads
/// every field at `base + offset`. Implemented by the derive macro for
/// any struct annotated with `#[derive(MemStruct)]`.
pub trait MemStruct: Sized {
    fn read_from(process: &dyn ReadProcess, base: u64) -> Result<Self>;
}

// ---------------------------------------------------------------------
// Primitive MemType + MemLayout impls
// ---------------------------------------------------------------------

macro_rules! impl_prim {
    ($ty:ty, $fn:ident) => {
        impl MemType for $ty {
            fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
                process::$fn(process, addr)
            }
        }
        impl MemLayout for $ty {
            const SIZE: usize = std::mem::size_of::<$ty>();
        }
    };
}

impl_prim!(u8, read_u8);
impl_prim!(u16, read_u16);
impl_prim!(u32, read_u32);
impl_prim!(u64, read_u64);
impl_prim!(i8, read_i8);
impl_prim!(i16, read_i16);
impl_prim!(i32, read_i32);
impl_prim!(i64, read_i64);
impl_prim!(f32, read_f32);
impl_prim!(f64, read_f64);
impl_prim!(bool, read_bool);

// ---------------------------------------------------------------------
// Fixed-length array reader
// ---------------------------------------------------------------------

/// Reads `[T; N]` element-by-element, striding by `T::SIZE`. Because
/// `[T; N]` can't be built without either `T: Default` or the unstable
/// `array::try_from_fn`, the MaybeUninit dance is done manually and any
/// partially-initialized prefix is cleaned up on a mid-read error.
impl<T: MemType + MemLayout, const N: usize> MemType for [T; N] {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        use std::mem::MaybeUninit;
        let stride = T::SIZE as u64;
        let mut out: [MaybeUninit<T>; N] =
            unsafe { MaybeUninit::<[MaybeUninit<T>; N]>::uninit().assume_init() };
        for i in 0..N {
            match T::read_from(process, addr + i as u64 * stride) {
                Ok(v) => out[i] = MaybeUninit::new(v),
                Err(e) => {
                    for slot in out.iter_mut().take(i) {
                        unsafe { slot.assume_init_drop() };
                    }
                    return Err(e);
                }
            }
        }
        // `out: [MaybeUninit<T>; N]` has no Drop of its own even if `T`
        // does (that's MaybeUninit's whole job), so leaving it to fall
        // out of scope after the read is a plain bitwise drop, not a
        // double-drop of the T values just moved out via `ptr.read()`.
        Ok(unsafe {
            let ptr = &out as *const _ as *const [T; N];
            ptr.read()
        })
    }
}

impl<T: MemLayout, const N: usize> MemLayout for [T; N] {
    const SIZE: usize = T::SIZE * N;
}
