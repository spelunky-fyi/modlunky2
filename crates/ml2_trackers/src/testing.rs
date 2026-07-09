//! Test fixtures for building fake entity maps + companion chains.
//! Split from the `#[cfg(test)]` block in `lib.rs` so
//! `chain_impl::inputs` tests can use the same builder for
//! companion-walk coverage.
//!
//! `EntityMapBuilder` assembles a `MockProcess`-ready byte buffer +
//! `UidEntityMap` that resolves `entity_map.get(process, uid)` to a
//! live `EntityHandle` for every added entity. Each added entity
//! carries an EntityDBEntry (for the type ID) and optional Player-
//! shaped extras (items vector + linked_companion_child) needed to
//! walk the HH chain in `ChainInputs::from_process`.

use crate::entity::EntityType;
use crate::entity_map::UidEntityMap;

/// Skeeto's low-bias 32-bit avalanche. Bit-for-bit copy of
/// `UidEntityMap::lowbias32` (private there); duplicated here rather
/// than exposed since the fixture is the only other caller.
pub fn lowbias32(mut x: u32) -> u32 {
    x ^= x >> 16;
    x = x.wrapping_mul(0x7FEB_352D);
    x ^= x >> 15;
    x = x.wrapping_mul(0x846C_A68B);
    x ^= x >> 16;
    x
}

/// Assembles a `MockProcess`-ready buffer + `UidEntityMap` such that a
/// consumer's `entity_map.get(process, uid)` walk resolves as if
/// against the live game.
///
/// Layout:
/// - 0x100..0x110: header {mask, table_ptr}. Address 0 is reserved so
///   a stray null pointer misreads as an empty entity, not the header.
/// - 0x120..0x120+cap*16: Robin Hood table entries.
/// - 0x10000, 0x10400, 0x10800, ...: one 0x400-byte slot per added
///   entity. Layout inside a slot:
///   - +0x08 (8 bytes): type_ptr to EntityDBEntry
///   - +0x18 (24 bytes): items EntityList. Zeroed by default (empty
///     list). `add_entity_with_hh_items` overwrites this with a
///     `[ent_list=0, uid_list=addr, cap=n, size=n]` layout pointing at
///     the item-UIDs array below.
///   - +0x38 (4 bytes): uid
///   - +0x150 (4 bytes): linked_companion_child (0 = end of chain)
///   - +0x200 (256 bytes): EntityDBEntry, id at +0x14
///   - +0x300..0x400: scratch area for the item-UIDs array (up to 64
///     u32 uids fit).
pub struct EntityMapBuilder {
    cap: u64,
    buffer: Vec<u8>,
    next_uid: u32,
    next_entity_idx: u32,
}

impl EntityMapBuilder {
    const HEADER_ADDR: u64 = 0x100;
    const TABLE_ADDR: u64 = 0x120;
    const ENTITY_BLOCK_START: u64 = 0x10000;
    const ENTITY_STRIDE: u64 = 0x400;
    const ENTITY_DB_OFFSET: u64 = 0x200;
    const ITEM_UIDS_OFFSET: u64 = 0x300;
    const ITEM_UIDS_MAX: usize = 64;

    pub fn new() -> Self {
        let cap = 256u64;
        let table_end = Self::TABLE_ADDR + cap * 16;
        let mut buffer = vec![0u8; table_end.max(0x1000) as usize];
        buffer[Self::HEADER_ADDR as usize..Self::HEADER_ADDR as usize + 8]
            .copy_from_slice(&(cap - 1).to_le_bytes());
        buffer[Self::HEADER_ADDR as usize + 8..Self::HEADER_ADDR as usize + 16]
            .copy_from_slice(&Self::TABLE_ADDR.to_le_bytes());
        Self {
            cap,
            buffer,
            next_uid: 1,
            next_entity_idx: 0,
        }
    }

    /// Uid the next `add_trivial_entity` call will assign. Tests read
    /// this both before adding (for `prev_next_uid`) and after (for
    /// `state.next_entity_uid`).
    pub fn next_uid(&self) -> u32 {
        self.next_uid
    }

    /// Add an entity with just its type_id set. Returns the uid.
    pub fn add_trivial_entity(&mut self, entity_type: EntityType) -> u32 {
        self.add_entity(entity_type, &[], 0)
    }

    /// Add several entities in order; returns their uids.
    pub fn add_trivial_entities(&mut self, types: &[EntityType]) -> Vec<u32> {
        types.iter().map(|&t| self.add_trivial_entity(t)).collect()
    }

    /// Add a companion entity whose `entity.items` vector references
    /// the given already-inserted uids. `linked_child_uid = 0` marks
    /// the end of the companion chain. Callers use `add_trivial_entities`
    /// for the held items first, then this to place the companion +
    /// record its uid as the main player's `linked_companion_child`.
    pub fn add_entity_with_hh_items(
        &mut self,
        entity_type: EntityType,
        held_item_uids: &[u32],
        linked_child_uid: u32,
    ) -> u32 {
        self.add_entity(entity_type, held_item_uids, linked_child_uid)
    }

    /// Core insertion. Writes EntityDBEntry.id at slot+0x214,
    /// Entity.type_ pointer at slot+0x08, Entity.uid at slot+0x38,
    /// Player.items EntityList at slot+0x18 pointing at the item-uids
    /// array, and Player.linked_companion_child at slot+0x150; then
    /// installs a Robin Hood table entry.
    fn add_entity(
        &mut self,
        entity_type: EntityType,
        held_item_uids: &[u32],
        linked_child_uid: u32,
    ) -> u32 {
        assert!(
            held_item_uids.len() <= Self::ITEM_UIDS_MAX,
            "too many held items ({}); slot fits {}",
            held_item_uids.len(),
            Self::ITEM_UIDS_MAX
        );
        let uid = self.next_uid;
        self.next_uid += 1;
        let idx = self.next_entity_idx;
        self.next_entity_idx += 1;
        let entity_addr = Self::ENTITY_BLOCK_START + idx as u64 * Self::ENTITY_STRIDE;
        let db_addr = entity_addr + Self::ENTITY_DB_OFFSET;
        let needed = (entity_addr + Self::ENTITY_STRIDE) as usize;
        if self.buffer.len() < needed {
            self.buffer.resize(needed, 0);
        }
        let e = entity_addr as usize;
        // Entity.type_ pointer at 0x08.
        self.buffer[e + 0x08..e + 0x10].copy_from_slice(&db_addr.to_le_bytes());
        // Entity.uid at 0x38.
        self.buffer[e + 0x38..e + 0x3C].copy_from_slice(&uid.to_le_bytes());
        // EntityDBEntry.id at +0x14.
        let d = db_addr as usize;
        self.buffer[d + 0x14..d + 0x18].copy_from_slice(&entity_type.0.to_le_bytes());

        // If the entity holds items, plant them in the slot's scratch
        // area and point Entity.items at that array.
        if !held_item_uids.is_empty() {
            let items_arr_addr = entity_addr + Self::ITEM_UIDS_OFFSET;
            let a = items_arr_addr as usize;
            for (i, &item_uid) in held_item_uids.iter().enumerate() {
                let off = a + i * 4;
                self.buffer[off..off + 4].copy_from_slice(&item_uid.to_le_bytes());
            }
            let count = held_item_uids.len() as u32;
            // EntityList at Entity+0x18: ent_list @ +0x00 (unused),
            // uid_list @ +0x08, cap @ +0x10, size @ +0x14.
            // ent_list left zeroed; the tracker never reads it.
            self.buffer[e + 0x20..e + 0x28].copy_from_slice(&items_arr_addr.to_le_bytes());
            self.buffer[e + 0x28..e + 0x2C].copy_from_slice(&count.to_le_bytes());
            self.buffer[e + 0x2C..e + 0x30].copy_from_slice(&count.to_le_bytes());
        }

        // Player.linked_companion_child at +0x150.
        self.buffer[e + 0x150..e + 0x154].copy_from_slice(&linked_child_uid.to_le_bytes());

        let hashed_key = lowbias32(uid.wrapping_add(1));
        self.insert_into_table(hashed_key, entity_addr);
        uid
    }

    /// Full Robin Hood insertion: probe from the home bucket, displace
    /// entries with a shorter PSL than the incoming key would have.
    /// Naive linear probing breaks the `target_psl > entry_psl`
    /// early-out in `UidEntityMap::find_addr` under certain collision
    /// patterns.
    fn insert_into_table(&mut self, mut cur_key: u32, mut cur_addr: u64) {
        let mask = self.cap - 1;
        let mut cur_index = (cur_key as u64) & mask;
        for _ in 0..self.cap {
            let entry_start = (Self::TABLE_ADDR + cur_index * 16) as usize;
            let existing_key = u32::from_le_bytes(
                self.buffer[entry_start..entry_start + 4]
                    .try_into()
                    .unwrap(),
            );
            if existing_key == 0 {
                self.buffer[entry_start..entry_start + 4].copy_from_slice(&cur_key.to_le_bytes());
                self.buffer[entry_start + 8..entry_start + 16]
                    .copy_from_slice(&cur_addr.to_le_bytes());
                return;
            }
            let existing_addr = u64::from_le_bytes(
                self.buffer[entry_start + 8..entry_start + 16]
                    .try_into()
                    .unwrap(),
            );
            let cur_psl = cur_index.wrapping_sub(cur_key as u64) & mask;
            let existing_psl = cur_index.wrapping_sub(existing_key as u64) & mask;
            if cur_psl > existing_psl {
                self.buffer[entry_start..entry_start + 4].copy_from_slice(&cur_key.to_le_bytes());
                self.buffer[entry_start + 8..entry_start + 16]
                    .copy_from_slice(&cur_addr.to_le_bytes());
                cur_key = existing_key;
                cur_addr = existing_addr;
            }
            cur_index = (cur_index + 1) & mask;
        }
        panic!("EntityMapBuilder: table full");
    }

    pub fn buffer(&self) -> &[u8] {
        &self.buffer
    }

    pub fn to_map(&self) -> UidEntityMap {
        UidEntityMap {
            mask: self.cap - 1,
            table_ptr: Self::TABLE_ADDR,
        }
    }
}

impl Default for EntityMapBuilder {
    fn default() -> Self {
        Self::new()
    }
}
