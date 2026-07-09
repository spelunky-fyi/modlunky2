//! `ml2_mem` reads structured data out of the running Spelunky 2
//! process into typed Rust values.
//!
//! The heart of the crate is the `MemStruct` derive from
//! `ml2_mem_derive`. Consumers describe game-state records as ordinary
//! Rust structs with `#[offset(N)]` annotations on each field; the
//! derive expands to a reader that walks the process at those offsets.
//!
//! Example:
//! ```ignore
//! use ml2_mem::MemStruct;
//!
//! #[derive(Debug, MemStruct)]
//! struct Inventory {
//!     #[offset(0x0)]  money: u32,
//!     #[offset(0x18)] kills_total: u32,
//! }
//!
//! #[derive(Debug, MemStruct)]
//! struct State {
//!     #[offset(0x30)] screen: i32,
//!     #[offset(0x14e0)] inventory: Inventory,
//! }
//! ```
//!
//! The abstraction layers:
//! - `ReadProcess`: raw "give me N bytes at this address" trait. The
//!   Windows backend calls `ReadProcessMemory`; the test mock reads
//!   from a `Vec<u8>`. Object-safe so higher-level readers all take
//!   `&dyn ReadProcess`.
//! - `MemType`: anything readable from an address (primitives,
//!   pointers, arrays, `MemStruct` types).
//! - `MemLayout`: compile-time size in the target process. Used by
//!   array and vector readers to stride between elements.
//! - `MemStruct`: offset-mapped records; emitted by the derive.
//!
//! MSVC primitives (`PolyPointer`, `Vector<T>`, `UnorderedMap<K, V>`),
//! the Windows `Process` implementation, and the feedcode scan
//! (`Spel2Process::get_feedcode`) all live here. Robin Hood
//! `UidEntityMap` is a game-specific entity index rather than a general
//! MSVC primitive, so it lives in `ml2_trackers::entity_map` next to
//! its consumers.

// Alias the crate to its external name so its own derive macros
// (which reference `::ml2_mem::MemStruct` etc) resolve when used in
// this crate's own tests / examples.
extern crate self as ml2_mem;

mod entity_uid_list;
mod error;
mod mem_type;
mod pointer;
mod poly_pointer;
mod process;
mod unordered_map;
mod vector;

pub use entity_uid_list::EntityUidList;
pub use error::{MemError, Result};
pub use mem_type::{MemLayout, MemStruct, MemType};
pub use pointer::Pointer;
pub use poly_pointer::PolyPointer;
pub use process::{
    FEEDCODE_MARKER, MockProcess, ReadProcess, SPEL2_EXE_NAME, Spel2Process, find_spelunky2_pid,
    read_bool, read_f32, read_f64, read_i8, read_i16, read_i32, read_i64, read_u8, read_u16,
    read_u32, read_u64,
};
pub use unordered_map::{UnorderedMap, UnorderedMapKey};
pub use vector::Vector;

pub use ml2_mem_derive::{MemEnum, MemStruct};

/// Const helper used by the `MemStruct` derive to fold field sizes into
/// a `MemLayout::SIZE` value. Exposed publicly so downstream authors who
/// hand-implement `MemLayout` for exotic layouts can reach for it too.
pub const fn const_max(a: usize, b: usize) -> usize {
    if a > b { a } else { b }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Debug, PartialEq, MemStruct)]
    struct SmallStruct {
        #[offset(0x0)]
        a: u32,
        #[offset(0x8)]
        b: u16,
        #[offset(0x10)]
        c: i32,
    }

    // Layout: a@0..4, b@8..10, c@16..20. Gap bytes stay zero.
    fn buf_for_small() -> Vec<u8> {
        let mut v = vec![0u8; 32];
        v[0..4].copy_from_slice(&0xDEADBEEFu32.to_le_bytes());
        v[8..10].copy_from_slice(&0x1234u16.to_le_bytes());
        v[16..20].copy_from_slice(&(-42i32).to_le_bytes());
        v
    }

    #[test]
    fn primitives_read_at_offsets() {
        let data = buf_for_small();
        let proc = MockProcess { data: &data };
        assert_eq!(read_u32(&proc, 0).unwrap(), 0xDEADBEEF);
        assert_eq!(read_u16(&proc, 8).unwrap(), 0x1234);
        assert_eq!(read_i32(&proc, 16).unwrap(), -42);
    }

    #[test]
    fn derive_reads_named_fields() {
        let data = buf_for_small();
        let proc = MockProcess { data: &data };
        let s = <SmallStruct as MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(
            s,
            SmallStruct {
                a: 0xDEADBEEF,
                b: 0x1234,
                c: -42,
            }
        );
    }

    #[test]
    fn derive_reads_at_nonzero_base() {
        // Same layout, but placed at offset 100 in the buffer.
        let mut data = vec![0u8; 200];
        data[100..104].copy_from_slice(&0xCAFEBABEu32.to_le_bytes());
        data[108..110].copy_from_slice(&0x0011u16.to_le_bytes());
        data[116..120].copy_from_slice(&7i32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let s = <SmallStruct as MemStruct>::read_from(&proc, 100).unwrap();
        assert_eq!(
            s,
            SmallStruct {
                a: 0xCAFEBABE,
                b: 0x0011,
                c: 7,
            }
        );
    }

    #[test]
    fn out_of_bounds_read_errors() {
        let data = vec![0u8; 4];
        let proc = MockProcess { data: &data };
        assert!(read_u64(&proc, 0).is_err());
    }

    #[test]
    fn pointer_null_returns_none() {
        let mut data = vec![0u8; 16];
        // Address 0 stored at 0..8 (null pointer).
        data[0..8].copy_from_slice(&0u64.to_le_bytes());
        let proc = MockProcess { data: &data };
        let ptr: Pointer<u32> = Pointer::read_from(&proc, 0).unwrap();
        assert!(ptr.is_null());
        assert_eq!(ptr.load(&proc).unwrap(), None);
    }

    #[test]
    fn pointer_load_follows_indirection() {
        // Pointer at 0 -> target at 100 -> u32 value 0xAABBCCDD.
        let mut data = vec![0u8; 200];
        data[0..8].copy_from_slice(&100u64.to_le_bytes());
        data[100..104].copy_from_slice(&0xAABBCCDDu32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let ptr: Pointer<u32> = Pointer::read_from(&proc, 0).unwrap();
        assert_eq!(ptr.addr, 100);
        assert_eq!(ptr.load(&proc).unwrap(), Some(0xAABBCCDD));
    }

    #[test]
    fn fixed_array_reads_elements() {
        // Four u32s starting at 0.
        let mut data = vec![0u8; 16];
        for (i, chunk) in data.chunks_mut(4).enumerate() {
            chunk.copy_from_slice(&(i as u32).to_le_bytes());
        }
        let proc = MockProcess { data: &data };
        let arr: [u32; 4] = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(arr, [0, 1, 2, 3]);
    }

    // Lays out a vector header + backing buffer of `values` u32s. The
    // header sits at address 0 (first/last/cap pointers); the backing
    // buffer starts at `buffer_base` in the same address space.
    fn build_vector_layout(values: &[u32], buffer_base: u64) -> Vec<u8> {
        let element_bytes = values.len() * 4;
        let end = (buffer_base as usize) + element_bytes;
        let mut data = vec![0u8; end.max(24)];
        // Header: first, last, capacity.
        data[0..8].copy_from_slice(&buffer_base.to_le_bytes());
        let last = buffer_base + element_bytes as u64;
        data[8..16].copy_from_slice(&last.to_le_bytes());
        data[16..24].copy_from_slice(&last.to_le_bytes()); // cap == last for simplicity
        for (i, v) in values.iter().enumerate() {
            let off = buffer_base as usize + i * 4;
            data[off..off + 4].copy_from_slice(&v.to_le_bytes());
        }
        data
    }

    #[test]
    fn vector_reports_length_from_pointer_delta() {
        let data = build_vector_layout(&[10, 20, 30], 64);
        let proc = MockProcess { data: &data };
        let v: Vector<u32> = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(v.len(), 3);
        assert!(!v.is_null());
    }

    #[test]
    fn vector_load_reads_every_element() {
        let data = build_vector_layout(&[100, 200, 300, 400], 40);
        let proc = MockProcess { data: &data };
        let v: Vector<u32> = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(v.load(&proc).unwrap(), vec![100, 200, 300, 400]);
    }

    #[test]
    fn vector_at_reads_single_element() {
        let data = build_vector_layout(&[7, 8, 9, 10, 11], 32);
        let proc = MockProcess { data: &data };
        let v: Vector<u32> = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(v.at(&proc, 2).unwrap(), 9);
        assert!(v.at(&proc, 5).is_err());
    }

    #[test]
    fn vector_null_is_empty() {
        let data = vec![0u8; 24];
        let proc = MockProcess { data: &data };
        let v: Vector<u32> = MemType::read_from(&proc, 0).unwrap();
        assert!(v.is_null());
        assert_eq!(v.len(), 0);
        assert!(v.load(&proc).unwrap().is_empty());
    }

    #[test]
    fn poly_pointer_load_base_and_load_as() {
        // At address 0, store a pointer to 100. At 100..108, store a
        // discriminant u32 (7) followed by another u32 (0xAA). load_base
        // reads the discriminant; load_as reads the wider concrete shape.
        let mut data = vec![0u8; 200];
        data[0..8].copy_from_slice(&100u64.to_le_bytes());
        data[100..104].copy_from_slice(&7u32.to_le_bytes());
        data[104..108].copy_from_slice(&0xAAu32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let ptr: PolyPointer<u32> = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(ptr.addr, 100);
        assert_eq!(ptr.load_base(&proc).unwrap(), Some(7));
        // Read a two-field struct at the same addr.
        #[derive(Debug, PartialEq, MemStruct)]
        struct Concrete {
            #[offset(0x0)]
            tag: u32,
            #[offset(0x4)]
            payload: u32,
        }
        assert_eq!(
            ptr.load_as::<Concrete>(&proc).unwrap(),
            Some(Concrete {
                tag: 7,
                payload: 0xAA
            })
        );
    }

    #[test]
    fn poly_pointer_null_returns_none() {
        let data = vec![0u8; 8];
        let proc = MockProcess { data: &data };
        let ptr: PolyPointer<u32> = MemType::read_from(&proc, 0).unwrap();
        assert!(ptr.is_null());
        assert_eq!(ptr.load_base(&proc).unwrap(), None);
        assert_eq!(ptr.load_as::<u64>(&proc).unwrap(), None);
        assert!(ptr.load_as_required::<u32>(&proc).is_err());
    }

    // -- MemLayout: derived struct size + nested struct arrays ------

    #[derive(Debug, PartialEq, MemStruct)]
    struct Nested {
        #[offset(0x0)]
        a: u32,
        #[offset(0x4)]
        b: u32,
    }

    #[test]
    fn derived_mem_layout_is_last_field_end() {
        // SmallStruct's last field is c: i32 @ 0x10; SIZE should be 0x14.
        assert_eq!(<SmallStruct as MemLayout>::SIZE, 0x14);
        assert_eq!(<Nested as MemLayout>::SIZE, 8);
    }

    #[test]
    fn nested_struct_array_strides_correctly() {
        // Two back-to-back Nested at 0 and 8. Third at 16.
        let mut data = vec![0u8; 24];
        data[0..4].copy_from_slice(&1u32.to_le_bytes());
        data[4..8].copy_from_slice(&2u32.to_le_bytes());
        data[8..12].copy_from_slice(&3u32.to_le_bytes());
        data[12..16].copy_from_slice(&4u32.to_le_bytes());
        data[16..20].copy_from_slice(&5u32.to_le_bytes());
        data[20..24].copy_from_slice(&6u32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let arr: [Nested; 3] = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(
            arr,
            [
                Nested { a: 1, b: 2 },
                Nested { a: 3, b: 4 },
                Nested { a: 5, b: 6 },
            ]
        );
    }

    // -- MemEnum -----------------------------------------------------

    #[repr(i32)]
    #[derive(Debug, PartialEq, Clone, Copy, MemEnum)]
    enum Screen {
        Logo = 0,
        Intro = 1,
        Menu = 2,
    }

    #[repr(u8)]
    #[derive(Debug, PartialEq, Clone, Copy, MemEnum)]
    enum Tag {
        A = 0,
        B = 0xFF,
    }

    #[repr(i32)]
    #[derive(Debug, PartialEq, Clone, Copy, MemEnum)]
    enum Signed {
        NegOne = -1,
        Zero = 0,
        One = 1,
    }

    #[test]
    fn mem_enum_reads_by_discriminant() {
        let mut data = vec![0u8; 4];
        data.copy_from_slice(&2i32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let s: Screen = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(s, Screen::Menu);
    }

    #[test]
    fn mem_enum_errors_on_unknown_discriminant() {
        let mut data = vec![0u8; 4];
        data.copy_from_slice(&99i32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let err = <Screen as MemType>::read_from(&proc, 0).unwrap_err();
        match err {
            MemError::BadEnum { ty, value } => {
                assert_eq!(ty, "Screen");
                assert_eq!(value, 99);
            }
            _ => panic!("expected BadEnum, got {err:?}"),
        }
    }

    #[test]
    fn mem_enum_u8_repr() {
        let data = vec![0xFFu8];
        let proc = MockProcess { data: &data };
        let t: Tag = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(t, Tag::B);
    }

    #[test]
    fn mem_enum_signed_discriminants() {
        let mut data = vec![0u8; 4];
        data.copy_from_slice(&(-1i32).to_le_bytes());
        let proc = MockProcess { data: &data };
        let v: Signed = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(v, Signed::NegOne);
    }

    #[test]
    fn mem_enum_layout_matches_repr() {
        assert_eq!(<Screen as MemLayout>::SIZE, 4);
        assert_eq!(<Tag as MemLayout>::SIZE, 1);
    }

    // -- Vector<T> as a MemStruct field ------------------------------
    //
    // Existing `vector_*` tests only exercise a top-level Vector read.
    // Real game structs (Entity.items, Inventory.player_bags, ...)
    // carry vectors inline; the derive has to hand-off to Vector's
    // MemType impl at the right offset and stride past the 24-byte
    // header so following fields still land correctly.

    #[derive(Debug, MemStruct)]
    struct VectorField {
        #[offset(0x0)]
        header: u32,
        #[offset(0x8)]
        items: Vector<u32>,
        #[offset(0x20)]
        footer: u32,
    }

    #[test]
    fn vector_as_named_struct_field_reads_at_offset() {
        // Header @ 0x0, Vector<u32> header @ 0x8..0x20, footer @ 0x20.
        // Backing buffer at 0x40 so it doesn't overlap the struct.
        let buffer_base: u64 = 0x40;
        let values: [u32; 3] = [11, 22, 33];
        let mut data = vec![0u8; (buffer_base as usize) + values.len() * 4];
        data[0..4].copy_from_slice(&0xDEAD_BEEFu32.to_le_bytes());
        // Vector<u32> header at 0x8..0x20: first, last, capacity.
        data[0x08..0x10].copy_from_slice(&buffer_base.to_le_bytes());
        let last = buffer_base + (values.len() as u64) * 4;
        data[0x10..0x18].copy_from_slice(&last.to_le_bytes());
        data[0x18..0x20].copy_from_slice(&last.to_le_bytes());
        data[0x20..0x24].copy_from_slice(&0xCAFEu32.to_le_bytes());
        for (i, v) in values.iter().enumerate() {
            let off = buffer_base as usize + i * 4;
            data[off..off + 4].copy_from_slice(&v.to_le_bytes());
        }
        let proc = MockProcess { data: &data };
        let obj = <VectorField as MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(obj.header, 0xDEAD_BEEF);
        assert_eq!(obj.items.len(), 3);
        assert_eq!(obj.items.load(&proc).unwrap(), vec![11, 22, 33]);
        assert_eq!(obj.footer, 0xCAFE);
    }

    #[test]
    fn vector_as_named_struct_field_layout_covers_vector_header() {
        // MemLayout::SIZE for VectorField must reach past the trailing
        // footer's own size (0x20 + 4 = 0x24). If it stopped short
        // (e.g. counted Vector as zero-size), a struct that placed a
        // VectorField inline followed by another field would silently
        // overlap.
        assert_eq!(<VectorField as MemLayout>::SIZE, 0x24);
    }

    // -- Vector<T> corrupt-data paths --------------------------------

    #[test]
    fn vector_with_last_before_first_is_empty() {
        // Corrupt torn read: `last < first` would produce a negative
        // element count with checked subtraction. `saturating_sub`
        // swallows it: length reports 0, load returns empty, no panic.
        let mut data = vec![0u8; 24];
        data[0..8].copy_from_slice(&0x100u64.to_le_bytes()); // first
        data[8..16].copy_from_slice(&0x80u64.to_le_bytes()); // last (< first)
        data[16..24].copy_from_slice(&0x100u64.to_le_bytes()); // capacity
        let proc = MockProcess { data: &data };
        let v: Vector<u32> = MemType::read_from(&proc, 0).unwrap();
        assert!(!v.is_null());
        assert_eq!(v.len(), 0);
        assert!(v.load(&proc).unwrap().is_empty());
    }

    #[test]
    fn vector_with_oversized_last_errors_on_load() {
        // `last` past the end of the buffer + a non-empty first ->
        // len() cheerfully returns a large number, but the actual
        // element read must fail with an out-of-bounds Read error, not
        // read garbage.
        let mut data = vec![0u8; 40];
        // first at 0x18 (right after the header); last at 0x1000000
        // (way past buffer end). capacity irrelevant.
        data[0..8].copy_from_slice(&0x18u64.to_le_bytes());
        data[8..16].copy_from_slice(&0x0100_0000u64.to_le_bytes());
        data[16..24].copy_from_slice(&0x0100_0000u64.to_le_bytes());
        // A single valid element at 0x18 so the FIRST read succeeds;
        // failure comes from the vast tail beyond the buffer.
        data[0x18..0x1C].copy_from_slice(&0xABCDu32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let v: Vector<u32> = MemType::read_from(&proc, 0).unwrap();
        assert!(v.len() > 1_000_000);
        assert!(v.load(&proc).is_err(), "load should reject OOB read");
    }

    // -- PolyPointer three-level inheritance chain -------------------
    //
    // Covers `Supreme` <- `Middle` <- `Lowest` where each derived type
    // adds one field. `load_as::<Concrete>` is fully generic, so a
    // single stored PolyPointer<Supreme> can decode as Supreme, Middle,
    // or Lowest from the same address without a re-read of the pointer.

    #[derive(Debug, PartialEq, MemStruct)]
    struct Supreme {
        #[offset(0x0)]
        tag: u32,
    }

    #[derive(Debug, PartialEq, MemStruct)]
    struct Middle {
        #[offset(0x0)]
        tag: u32,
        #[offset(0x4)]
        middle_field: u32,
    }

    #[derive(Debug, PartialEq, MemStruct)]
    struct Lowest {
        #[offset(0x0)]
        tag: u32,
        #[offset(0x4)]
        middle_field: u32,
        #[offset(0x8)]
        lowest_field: u32,
    }

    #[test]
    fn poly_pointer_inheritance_chain_load_as_each_level() {
        // Instance of `Lowest` at address 100. PolyPointer<Supreme>
        // stored at 0 references it.
        let mut data = vec![0u8; 200];
        data[0..8].copy_from_slice(&100u64.to_le_bytes());
        data[100..104].copy_from_slice(&7u32.to_le_bytes()); // tag
        data[104..108].copy_from_slice(&11u32.to_le_bytes()); // middle_field
        data[108..112].copy_from_slice(&13u32.to_le_bytes()); // lowest_field
        let proc = MockProcess { data: &data };

        let ptr: PolyPointer<Supreme> = MemType::read_from(&proc, 0).unwrap();
        assert_eq!(ptr.load_base(&proc).unwrap(), Some(Supreme { tag: 7 }));
        assert_eq!(
            ptr.load_as::<Middle>(&proc).unwrap(),
            Some(Middle {
                tag: 7,
                middle_field: 11,
            })
        );
        assert_eq!(
            ptr.load_as::<Lowest>(&proc).unwrap(),
            Some(Lowest {
                tag: 7,
                middle_field: 11,
                lowest_field: 13,
            })
        );
    }

    // -- Pointer<T> / PolyPointer<T> as struct fields ----------------

    #[derive(Debug, MemStruct)]
    struct PointerFields {
        #[offset(0x0)]
        pointed_int: Pointer<u32>,
        #[offset(0x8)]
        poly_child: PolyPointer<Supreme>,
    }

    #[test]
    fn pointer_and_poly_pointer_as_named_fields() {
        // pointed_int at 0x0 -> address 100 (u32 value there).
        // poly_child at 0x8 -> address 108 (Supreme fields there).
        let mut data = vec![0u8; 200];
        data[0..8].copy_from_slice(&100u64.to_le_bytes());
        data[8..16].copy_from_slice(&108u64.to_le_bytes());
        data[100..104].copy_from_slice(&0xAA_BB_CC_DDu32.to_le_bytes());
        data[108..112].copy_from_slice(&42u32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let obj = <PointerFields as MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(obj.pointed_int.addr, 100);
        assert_eq!(obj.pointed_int.load(&proc).unwrap(), Some(0xAA_BB_CC_DD));
        assert_eq!(obj.poly_child.addr, 108);
        assert_eq!(
            obj.poly_child.load_base(&proc).unwrap(),
            Some(Supreme { tag: 42 })
        );
    }

    // -- Nested MemStruct as a named field at non-zero offset --------
    //
    // The `[Nested; N]` test proves array striding works. The derive
    // path is different for arrays (via the [T; N] MemType impl) vs a
    // bare `Nested` field (via the derived Nested::read_from), so both
    // shapes need coverage.

    #[derive(Debug, PartialEq, MemStruct)]
    struct Outer {
        #[offset(0x0)]
        header: u32,
        #[offset(0x10)]
        inner: Nested,
        #[offset(0x20)]
        footer: u32,
    }

    #[test]
    fn nested_memstruct_as_named_field_reads_at_offset() {
        let mut data = vec![0u8; 40];
        data[0..4].copy_from_slice(&0x11_11_11_11u32.to_le_bytes());
        // Nested @ 0x10: a @ 0x10, b @ 0x14.
        data[0x10..0x14].copy_from_slice(&0x22_22_22_22u32.to_le_bytes());
        data[0x14..0x18].copy_from_slice(&0x33_33_33_33u32.to_le_bytes());
        data[0x20..0x24].copy_from_slice(&0x44_44_44_44u32.to_le_bytes());
        let proc = MockProcess { data: &data };
        let outer = <Outer as MemStruct>::read_from(&proc, 0).unwrap();
        assert_eq!(outer.header, 0x11_11_11_11);
        assert_eq!(
            outer.inner,
            Nested {
                a: 0x22_22_22_22,
                b: 0x33_33_33_33,
            }
        );
        assert_eq!(outer.footer, 0x44_44_44_44);
    }

    #[test]
    fn nested_memstruct_layout_reaches_past_last_field() {
        // Outer's last field is `footer: u32 @ 0x20`; SIZE = 0x24.
        assert_eq!(<Outer as MemLayout>::SIZE, 0x24);
    }
}
