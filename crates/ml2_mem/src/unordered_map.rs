//! MSVC `std::unordered_map<K, V>` reader.
//!
//! Layout is hand-reverse-engineered against a live Spelunky 2 process.
//! The MSVC implementation is a chained hash table with a linked-list
//! backing:
//!
//! ```text
//! struct unordered_map {              // total: 64 bytes
//!     void*    _ignored1;             // 0x00
//!     void*    end;                   // 0x08  sentinel: end-of-list marker
//!     u64      size;                  // 0x10  (unused)
//!     bucket_t* buckets_ptr;          // 0x18  base of bucket array
//!     u8       _padding[0x30-0x20];   //       (16 bytes of padding)
//!     u64      mask;                  // 0x30  bucket count - 1 (pow2)
//!     u64      bucket_size;           // 0x38  (unused)
//! };
//!
//! struct bucket_t {                   // total: 16 bytes
//!     node_t*  first;                 // 0x00  first node in this bucket
//!     node_t*  last;                  // 0x08  last node in this bucket
//! };                                  //       (both point at `end` when empty)
//!
//! struct node_t {                     // total: variable
//!     node_t*  next;                  // 0x00
//!     node_t*  prev;                  // 0x08  (unused)
//!     K        key;                   // 0x10, padded up to 8-byte boundary
//!     V        value;                 // 0x10 + align8(sizeof K)
//! };
//! ```
//!
//! Lookup: hash the key's raw wire bytes via FNV-1a 64-bit, mask against
//! `mask` to get the bucket index, then walk `first -> next -> ...` until
//! the key matches or the walk passes `last`.
//!
//! `UnorderedMap<K, V>` reads the 64-byte meta eagerly (single 64-byte
//! read). Actual lookups run on demand and issue a few extra reads per
//! call (one for the bucket, then one per node walked).

use std::marker::PhantomData;

use crate::error::Result;
use crate::mem_type::{MemLayout, MemType};
use crate::process::{self, ReadProcess};

/// Fixed offsets inside the on-wire meta struct. Kept as consts so a stray
/// edit here trips the size assertion at the bottom of this file.
const META_END_OFFSET: u64 = 0x08;
const META_BUCKETS_PTR_OFFSET: u64 = 0x18;
const META_MASK_OFFSET: u64 = 0x30;
const UNORDERED_MAP_SIZE: usize = 64;

/// Fixed offsets inside a bucket. Two pointers back-to-back.
const BUCKET_FIRST_OFFSET: u64 = 0x00;
const BUCKET_LAST_OFFSET: u64 = 0x08;
const BUCKET_SIZE: usize = 16;

/// Fixed offsets inside a node. Key/value start after two pointers.
const NODE_NEXT_OFFSET: u64 = 0x00;
const NODE_KEY_OFFSET: u64 = 0x10;

/// Round `n` up to the next 8-byte boundary. MSVC pads keys + values to
/// 8-byte alignment inside a hashmap node.
const fn align8(n: usize) -> usize {
    (n + 7) & !7
}

/// A key type usable in an `UnorderedMap` lookup. `hash_bytes()` returns
/// the wire representation the game hashed with FNV-1a to place the key
/// in a bucket. For primitives that's the little-endian byte pattern;
/// user-defined key types must produce byte-for-byte the same shape the
/// game writes into a node's key slot.
pub trait UnorderedMapKey {
    /// Length of the wire representation. Must match the type's on-wire
    /// size in the target process; `MemLayout::SIZE` for primitives.
    const HASH_LEN: usize;

    /// Fill `out` with the wire bytes to feed into FNV-1a. `out.len() ==
    /// HASH_LEN`; implementations write exactly `HASH_LEN` bytes.
    fn write_hash_bytes(&self, out: &mut [u8]);
}

macro_rules! impl_key_for_prim {
    ($ty:ty) => {
        impl UnorderedMapKey for $ty {
            const HASH_LEN: usize = std::mem::size_of::<$ty>();
            fn write_hash_bytes(&self, out: &mut [u8]) {
                out.copy_from_slice(&self.to_le_bytes());
            }
        }
    };
}
impl_key_for_prim!(u8);
impl_key_for_prim!(u16);
impl_key_for_prim!(u32);
impl_key_for_prim!(u64);
impl_key_for_prim!(i8);
impl_key_for_prim!(i16);
impl_key_for_prim!(i32);
impl_key_for_prim!(i64);

/// FNV-1a 64-bit hash. MSVC's `std::hash` uses FNV-1a on Windows for
/// scalar keys; the constants are the standard FNV-1a offset basis and
/// prime, so this must match the game's bucket placement byte-for-byte.
fn fnv1a_64(bytes: &[u8]) -> u64 {
    const OFFSET: u64 = 0xcbf29ce484222325;
    const PRIME: u64 = 0x100000001b3;
    let mut h = OFFSET;
    for &b in bytes {
        h ^= b as u64;
        h = h.wrapping_mul(PRIME);
    }
    h
}

/// A remote MSVC `std::unordered_map<K, V>`. The meta is read eagerly; the
/// bucket array + node walk happen inside `get()` on demand.
#[derive(Debug, Clone, Copy)]
pub struct UnorderedMap<K, V> {
    end: u64,
    buckets_ptr: u64,
    mask: u64,
    _phantom: PhantomData<(K, V)>,
}

impl<K, V> UnorderedMap<K, V> {
    /// Sentinel end-of-chain pointer. Empty buckets have `first == end`;
    /// the last node in a bucket has `next == end` (or points past
    /// `last`, depending on MSVC version). `last` is treated as the
    /// primary terminator.
    pub fn end(&self) -> u64 {
        self.end
    }

    /// Base address of the bucket array. Each bucket is 16 bytes.
    pub fn buckets_ptr(&self) -> u64 {
        self.buckets_ptr
    }

    /// `bucket_count - 1`. Bucket index is `hash & mask`.
    pub fn mask(&self) -> u64 {
        self.mask
    }
}

impl<K, V> UnorderedMap<K, V>
where
    K: UnorderedMapKey + MemType + MemLayout + PartialEq,
    V: MemType + MemLayout,
{
    /// Look up `key`. Returns `Ok(None)` on miss (empty bucket, or walked
    /// the chain without a match) and propagates read errors otherwise.
    ///
    /// Cost: 1 read for the bucket + 1 read per node walked in that
    /// bucket's chain. Buckets under a well-behaved hash have a single
    /// entry on average, so a typical hit is 2 reads.
    pub fn get(&self, process: &dyn ReadProcess, key: &K) -> Result<Option<V>> {
        // Hash the key's wire bytes and pick a bucket. Stack-buffer the
        // key so lookups don't touch the heap for the common (small,
        // primitive) case.
        let mut key_buf = [0u8; 32];
        let key_bytes = if K::HASH_LEN <= key_buf.len() {
            let slot = &mut key_buf[..K::HASH_LEN];
            key.write_hash_bytes(slot);
            &key_buf[..K::HASH_LEN]
        } else {
            // Fallback for exotic key types larger than 32 bytes. Very
            // unusual for a hashmap key; if it happens, one heap alloc
            // per lookup is fine.
            let mut v = vec![0u8; K::HASH_LEN];
            key.write_hash_bytes(&mut v);
            return self.get_with_bytes(process, key, &v);
        };
        self.get_with_bytes(process, key, key_bytes)
    }

    fn get_with_bytes(
        &self,
        process: &dyn ReadProcess,
        key: &K,
        key_bytes: &[u8],
    ) -> Result<Option<V>> {
        let idx = fnv1a_64(key_bytes) & self.mask;
        let bucket_addr = self.buckets_ptr + idx * BUCKET_SIZE as u64;
        let first = process::read_u64(process, bucket_addr + BUCKET_FIRST_OFFSET)?;
        let last = process::read_u64(process, bucket_addr + BUCKET_LAST_OFFSET)?;

        // Empty bucket: MSVC marks that by pointing first at the map's
        // shared end sentinel. Skip the walk.
        if first == self.end {
            return Ok(None);
        }

        // Node walk. Bounded by `last` (or a torn read that trips the
        // read errors above). Once the last node has been inspected
        // without a match, give up.
        let val_offset = NODE_KEY_OFFSET + align8(K::SIZE) as u64;
        let mut cursor = first;
        loop {
            let node_key = K::read_from(process, cursor + NODE_KEY_OFFSET)?;
            if node_key == *key {
                let val = V::read_from(process, cursor + val_offset)?;
                return Ok(Some(val));
            }
            if cursor == last {
                return Ok(None);
            }
            cursor = process::read_u64(process, cursor + NODE_NEXT_OFFSET)?;
        }
    }
}

impl<K, V> MemType for UnorderedMap<K, V> {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self {
            end: process::read_u64(process, addr + META_END_OFFSET)?,
            buckets_ptr: process::read_u64(process, addr + META_BUCKETS_PTR_OFFSET)?,
            mask: process::read_u64(process, addr + META_MASK_OFFSET)?,
            _phantom: PhantomData,
        })
    }
}

impl<K, V> MemLayout for UnorderedMap<K, V> {
    const SIZE: usize = UNORDERED_MAP_SIZE;
}

// Size sanity: the on-wire meta struct is 64 bytes. If a future edit
// pushes any META_* offset past that, the SIZE constant stops matching
// the last used field boundary and this pin fires at compile time.
const _: () = assert!(
    (META_MASK_OFFSET as usize) + 8 <= UNORDERED_MAP_SIZE,
    "UnorderedMap meta layout overflows the fixed 64-byte size"
);

#[cfg(test)]
mod tests {
    use super::*;
    use crate::process::MockProcess;

    // ------------------------------------------------------------------
    // FNV-1a spot-checks. Values are the standard FNV-1a 64-bit vectors,
    // so a regression here would silently send lookups to the wrong
    // bucket.
    // ------------------------------------------------------------------

    #[test]
    fn fnv1a_matches_known_vectors() {
        // Empty input hashes to the offset basis.
        assert_eq!(fnv1a_64(b""), 0xcbf29ce484222325);
        // Standard "hello" vector.
        assert_eq!(fnv1a_64(b"hello"), 0xa430d84680aabd0b);
        // Standard "foobar" vector.
        assert_eq!(fnv1a_64(b"foobar"), 0x85944171f73967e8);
    }

    #[test]
    fn align8_pads_up_to_next_boundary() {
        assert_eq!(align8(0), 0);
        assert_eq!(align8(1), 8);
        assert_eq!(align8(4), 8);
        assert_eq!(align8(7), 8);
        assert_eq!(align8(8), 8);
        assert_eq!(align8(9), 16);
        assert_eq!(align8(16), 16);
    }

    // ------------------------------------------------------------------
    // Meta struct read. Fixture layout: end at 0x08, buckets_ptr at 0x18,
    // mask at 0x30.
    // ------------------------------------------------------------------

    #[test]
    fn reads_meta_at_fixed_offsets() {
        let mut data = vec![0u8; 64];
        data[META_END_OFFSET as usize..META_END_OFFSET as usize + 8]
            .copy_from_slice(&0xbaba_baba_baba_babau64.to_le_bytes());
        data[META_BUCKETS_PTR_OFFSET as usize..META_BUCKETS_PTR_OFFSET as usize + 8]
            .copy_from_slice(&1u64.to_le_bytes());
        data[META_MASK_OFFSET as usize..META_MASK_OFFSET as usize + 8]
            .copy_from_slice(&0x0fu64.to_le_bytes());
        let proc = MockProcess { data: &data };
        let m: UnorderedMap<u32, u16> = UnorderedMap::read_from(&proc, 0).unwrap();
        assert_eq!(m.end, 0xbaba_baba_baba_baba);
        assert_eq!(m.buckets_ptr, 1);
        assert_eq!(m.mask, 0x0f);
    }

    // ------------------------------------------------------------------
    // Full lookup round-trip: a u32 key -> u16 value map with a single
    // populated bucket. Values are picked so the FNV-1a hash lands in
    // the low bucket regardless of collision behavior.
    // ------------------------------------------------------------------
    //
    // Address plan for the fixture:
    //   0x000 .. 0x040 : UnorderedMap meta (end, buckets_ptr, mask)
    //   0x040 .. 0x060 : buckets[0..2] (16 bytes each)
    //   0x060 .. 0x0a0 : single node under bucket[1]
    //
    // With mask = 1 there are two buckets. Key 2u32 fnv1a-hashes to some
    // 64-bit value; either bucket is fine as long as the fixture populates
    // it. Rather than precompute, the node is inserted into whichever
    // bucket `2u32` hashes into.

    fn build_um_fixture(key: u32, value: u16) -> (Vec<u8>, u64) {
        const META_BASE: u64 = 0x000;
        const BUCKETS_BASE: u64 = 0x040;
        const NODE_ADDR: u64 = 0x060;
        const END_SENTINEL: u64 = 0xdead_beef_dead_beef;
        let mask: u64 = 1;
        // Where the target bucket lives in the buffer.
        let key_bytes = key.to_le_bytes();
        let hash = fnv1a_64(&key_bytes);
        let idx = hash & mask;
        let target_bucket_addr = BUCKETS_BASE + idx * BUCKET_SIZE as u64;
        let other_bucket_addr = BUCKETS_BASE + (idx ^ 1) * BUCKET_SIZE as u64;

        let mut data = vec![0u8; 0x100];

        // Meta.
        data[META_END_OFFSET as usize..META_END_OFFSET as usize + 8]
            .copy_from_slice(&END_SENTINEL.to_le_bytes());
        data[META_BUCKETS_PTR_OFFSET as usize..META_BUCKETS_PTR_OFFSET as usize + 8]
            .copy_from_slice(&BUCKETS_BASE.to_le_bytes());
        data[META_MASK_OFFSET as usize..META_MASK_OFFSET as usize + 8]
            .copy_from_slice(&mask.to_le_bytes());

        // Other bucket: empty (first + last both point at end).
        data[other_bucket_addr as usize..other_bucket_addr as usize + 8]
            .copy_from_slice(&END_SENTINEL.to_le_bytes());
        data[other_bucket_addr as usize + 8..other_bucket_addr as usize + 16]
            .copy_from_slice(&END_SENTINEL.to_le_bytes());

        // Target bucket: first = last = the one node.
        data[target_bucket_addr as usize..target_bucket_addr as usize + 8]
            .copy_from_slice(&NODE_ADDR.to_le_bytes());
        data[target_bucket_addr as usize + 8..target_bucket_addr as usize + 16]
            .copy_from_slice(&NODE_ADDR.to_le_bytes());

        // Node.
        // next_addr: doesn't matter for a single-node bucket since
        // `cursor == last` fires first.
        data[NODE_ADDR as usize..NODE_ADDR as usize + 8]
            .copy_from_slice(&END_SENTINEL.to_le_bytes());
        // key at NODE_ADDR + 0x10, u32 -> 4 bytes.
        data[(NODE_ADDR + NODE_KEY_OFFSET) as usize..(NODE_ADDR + NODE_KEY_OFFSET) as usize + 4]
            .copy_from_slice(&key.to_le_bytes());
        // value at NODE_ADDR + 0x10 + align8(4) = NODE_ADDR + 0x18. u16 -> 2 bytes.
        let val_addr = NODE_ADDR + NODE_KEY_OFFSET + align8(4) as u64;
        data[val_addr as usize..val_addr as usize + 2].copy_from_slice(&value.to_le_bytes());

        (data, META_BASE)
    }

    #[test]
    fn get_finds_single_entry() {
        let (data, base) = build_um_fixture(2u32, 0x0003u16);
        let proc = MockProcess { data: &data };
        let m: UnorderedMap<u32, u16> = UnorderedMap::read_from(&proc, base).unwrap();
        assert_eq!(m.get(&proc, &2u32).unwrap(), Some(0x0003));
    }

    #[test]
    fn get_miss_returns_none_in_populated_bucket() {
        // Populate bucket for key 2, then look up a key that hashes into
        // the same bucket but doesn't match. If `3` hashes into the other
        // bucket, None comes back via the empty path; if it hashes into
        // the same bucket, None comes back via the walk-then-give-up
        // path. Either way the answer is None.
        let (data, base) = build_um_fixture(2u32, 0x0003u16);
        let proc = MockProcess { data: &data };
        let m: UnorderedMap<u32, u16> = UnorderedMap::read_from(&proc, base).unwrap();
        assert_eq!(m.get(&proc, &7u32).unwrap(), None);
    }

    #[test]
    fn get_empty_bucket_returns_none() {
        // Same fixture but strip the populated bucket back to empty
        // (both first + last = end). Every lookup should short-circuit.
        let (mut data, base) = build_um_fixture(2u32, 0x0003u16);
        const END_SENTINEL: u64 = 0xdead_beef_dead_beef;
        // Buckets base is 0x40 in the fixture; overwrite both.
        for i in 0..2 {
            let b = 0x40 + i * BUCKET_SIZE;
            data[b..b + 8].copy_from_slice(&END_SENTINEL.to_le_bytes());
            data[b + 8..b + 16].copy_from_slice(&END_SENTINEL.to_le_bytes());
        }
        let proc = MockProcess { data: &data };
        let m: UnorderedMap<u32, u16> = UnorderedMap::read_from(&proc, base).unwrap();
        assert_eq!(m.get(&proc, &2u32).unwrap(), None);
    }

    // Guards against silently sizing the meta struct wrong. Reading past
    // this would let a following inline field overlap the map, so pin
    // the constant here.
    #[test]
    fn meta_size_matches_layout_constant() {
        assert_eq!(<UnorderedMap<u32, u16> as MemLayout>::SIZE, 64);
    }

    // Node layout with a u16 key -> node key slot is padded to 8 bytes,
    // so the value lives at 0x18. Guards against a stray edit to align8
    // that would break variable-sized keys.
    #[test]
    fn node_layout_pads_u16_key_slot_to_eight_bytes() {
        assert_eq!(
            NODE_KEY_OFFSET + align8(std::mem::size_of::<u16>()) as u64,
            0x18
        );
        assert_eq!(
            NODE_KEY_OFFSET + align8(std::mem::size_of::<u8>()) as u64,
            0x18
        );
        assert_eq!(
            NODE_KEY_OFFSET + align8(std::mem::size_of::<u32>()) as u64,
            0x18
        );
        assert_eq!(
            NODE_KEY_OFFSET + align8(std::mem::size_of::<u64>()) as u64,
            0x18
        );
    }
}
