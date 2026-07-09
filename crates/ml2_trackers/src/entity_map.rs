//! `UidEntityMap`: view of the game's Robin Hood open-addressing
//! hashmap that indexes live entities by UID.
//!
//! On the wire, the map header is two u64s:
//!
//! ```text
//! struct RobinHoodTableMeta {
//!     u64 mask;       // 0x00, table capacity minus 1 (always 2^k - 1)
//!     u64 table_ptr;  // 0x08, pointer to the entry array
//! };
//! ```
//!
//! Each entry is 16 bytes:
//!
//! ```text
//! struct RobinHoodTableEntry {
//!     u32 hashed_key;    // 0x00, lowbias32(uid + 1); 0 = empty slot
//!     u32 _pad;          // 0x04
//!     u64 entity_addr;   // 0x08, address of the Entity for this UID
//! };
//! ```
//!
//! Lookup uses linear probing but with Robin Hood ordering: entries
//! with a longer probe sequence displace entries with a shorter one,
//! so a lookup can stop as soon as it sees an entry whose PSL is
//! shorter than the target's would be, the target must not exist.
//!
//! The `_lowbias32` hasher (from https://github.com/skeeto/hash-prospector)
//! must match the exe bit-for-bit; every multiplication is masked to 32
//! bits before the next XOR shift via the wrapping u32 arithmetic.

use ml2_mem::{MemLayout, MemStruct, MemType, ReadProcess, Result};

use crate::entity::Entity;

/// The map header on the wire. Reads two u64s; hand-implemented
/// rather than deriving MemStruct since nothing else needs the derive.
#[derive(Debug, Clone, Copy)]
pub struct UidEntityMap {
    pub mask: u64,
    pub table_ptr: u64,
}

/// One entry from the underlying Robin Hood table. Exposed for tests +
/// debugging; production callers should stick to `.get()`.
#[derive(Debug, Clone, Copy, MemStruct)]
pub struct RobinHoodTableEntry {
    #[offset(0x0)]
    pub hashed_key: u32,
    #[offset(0x8)]
    pub entity_addr: u64,
}

impl RobinHoodTableEntry {
    pub const IN_MEMORY_SIZE: usize = 16;
}

/// Successful lookup result. Carries the raw entity address (so
/// callers can decode as a different concrete subtype) and the loaded
/// base `Entity` (so the common `type_.id` check doesn't need a second
/// read).
#[derive(Debug)]
pub struct EntityHandle {
    pub addr: u64,
    pub entity: Entity,
}

impl UidEntityMap {
    /// Skeeto's low-bias 32-bit avalanche. Bit-for-bit match required;
    /// any single-bit deviation from the exe's hasher produces silently
    /// wrong lookups on every table probe.
    #[inline]
    fn lowbias32(mut x: u32) -> u32 {
        x ^= x >> 16;
        x = x.wrapping_mul(0x7FEB_352D);
        x ^= x >> 15;
        x = x.wrapping_mul(0x846C_A68B);
        x ^= x >> 16;
        x
    }

    /// Look up the entity for `uid` and return its address + loaded
    /// base type. Returns `Ok(None)` for any "not present" case:
    /// null table, uid == -1 sentinel, miss, unreadable entity, or a
    /// UID-mismatch on the loaded entity (torn read or a slot that was
    /// reused mid-lookup).
    pub fn get(&self, process: &dyn ReadProcess, uid: i32) -> Result<Option<EntityHandle>> {
        if self.table_ptr == 0 {
            return Ok(None);
        }
        // -1 is the game's null-uid sentinel; walking a linked companion
        // chain terminates here.
        if uid == -1 {
            return Ok(None);
        }
        let Some(addr) = self.find_addr(process, uid)? else {
            return Ok(None);
        };
        // The `entity.uid != uid` guard: entries in the table are
        // keyed by hash, not UID, so a hash collision or a stale entry
        // pointing at an entity that no longer has this UID would
        // otherwise slip through. Drop silently; a future tracing hook
        // could log the mismatch if tracker logs need to be louder.
        let entity = <Entity as MemType>::read_from(process, addr)?;
        if entity.uid != uid as u32 {
            return Ok(None);
        }
        Ok(Some(EntityHandle { addr, entity }))
    }

    /// Walk the probe sequence for `uid` and return the address the
    /// table records for it, or None on miss. Kept separate so the
    /// probing logic can be unit-tested without needing a full Entity
    /// present at the target address.
    fn find_addr(&self, process: &dyn ReadProcess, uid: i32) -> Result<Option<u64>> {
        let target_key = Self::lowbias32((uid as u32).wrapping_add(1));
        // Table capacity is `mask + 1` (power-of-two sized), so
        // `x & mask` gives a valid index.
        let mask = self.mask;
        let mut cur_index = (target_key as u64) & mask;
        // Bound the loop by table capacity so a corrupted table can't
        // spin forever.
        let cap = mask.saturating_add(1);
        for _ in 0..cap {
            let entry_addr = self
                .table_ptr
                .checked_add(cur_index * RobinHoodTableEntry::IN_MEMORY_SIZE as u64)
                .ok_or_else(|| ml2_mem::MemError::Read {
                    addr: self.table_ptr,
                    msg: "table probe address overflow".into(),
                })?;
            let entry: RobinHoodTableEntry =
                <RobinHoodTableEntry as MemStruct>::read_from(process, entry_addr)?;
            if entry.hashed_key == target_key {
                return Ok(Some(entry.entity_addr));
            }
            if entry.hashed_key == 0 {
                // Empty slot before finding the key: the key is not
                // in the table.
                return Ok(None);
            }
            // PSL = probe sequence length: how far this entry (or the
            // target) is from its home bucket, computed under the same
            // mask. Robin Hood ordering guarantees stored entries'
            // PSLs monotonically decrease along the probe sequence
            // from the target's home. Finding an entry with a shorter
            // PSL than the target would have means the target would
            // have displaced it during insertion, so the target must
            // not be in the table.
            let target_psl = (cur_index.wrapping_sub(target_key as u64)) & mask;
            let entry_psl = (cur_index.wrapping_sub(entry.hashed_key as u64)) & mask;
            if target_psl > entry_psl {
                return Ok(None);
            }
            cur_index = (cur_index + 1) & mask;
        }
        // Exhausted the whole table without a hit or an empty slot.
        // In practice this only happens on a fully-populated + torn
        // table; treat as "not present" so a bad table doesn't crash
        // the tracker.
        Ok(None)
    }
}

impl MemType for UidEntityMap {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self {
            mask: u64::read_from(process, addr)?,
            table_ptr: u64::read_from(process, addr + 8)?,
        })
    }
}

impl MemLayout for UidEntityMap {
    const SIZE: usize = 16;
}
