//! Entity + Inventory + Player + related types.
//!
//! `EntityType` is a `u32` newtype so named constants (generated from
//! `entities.json` into `entity_types.rs`) work without paying the
//! cost of a 900-variant enum. Trackers get name-based comparisons
//! via those constants and set membership via `EntitySet` helpers.
//!
//! Struct offsets are declared via `#[offset(0x...)]`; the `MemStruct`
//! derive handles the actual reading.

use ml2_mem::{
    EntityUidList, MemEnum, MemLayout, MemStruct, MemType, Pointer, PolyPointer, ReadProcess,
    Result,
};

/// Newtype wrapping the raw entity type ID from the exe. Stored as
/// `u32` on the wire so name lookups round-trip. Constants live in
/// `entity_types.rs`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct EntityType(pub u32);

impl MemType for EntityType {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self(u32::read_from(process, addr)?))
    }
}

impl MemLayout for EntityType {
    const SIZE: usize = 4;
}

/// FRONT / BACK layer flag. Stored as `u8` on disk.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, MemEnum)]
pub enum Layer {
    Front = 0,
    Back = 1,
}

/// Character state machine values. All 31 slots because the exe reads
/// unknown values too; the "UNKNOWN" variants leave those slots named.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, MemEnum)]
pub enum CharState {
    Flailing = 0,
    Standing = 1,
    Sitting = 2,
    Unknown1 = 3,
    Hanging = 4,
    Ducking = 5,
    Climbing = 6,
    Pushing = 7,
    Jumping = 8,
    Falling = 9,
    Dropping = 10,
    Unknown2 = 11,
    Attacking = 12,
    Unknown3 = 13,
    Unknown4 = 14,
    Unknown5 = 15,
    Unknown6 = 16,
    Throwing = 17,
    Stunned = 18,
    Entering = 19,
    Loading = 20,
    Exiting = 21,
    Dying = 22,
    Unknown7 = 23,
    Unknown8 = 24,
    Unknown9 = 25,
    Unknown10 = 26,
    Unknown11 = 27,
    Unknown12 = 28,
    Unknown13 = 29,
    Unknown14 = 30,
}

/// Small "just the type ID" view of the game's EntityDB entry. The
/// entry is 256 bytes on the wire; only `id` at offset 0x14 matters
/// to trackers.
#[derive(Debug, MemStruct)]
pub struct EntityDBEntry {
    #[offset(0x14)]
    pub id: EntityType,
}

/// EntityDB entries are 256 bytes. Not derivable because there is no
/// 256th offset declared; hand-implement so arrays / vectors of
/// `EntityDBEntry` stride correctly.
impl EntityDBEntry {
    pub const IN_MEMORY_SIZE: usize = 256;
}

/// "Core" Entity fields shared by every subclass. Split from `Entity`
/// so the `overlay` field's poly-pointer type can reference `Entity`
/// (which extends this) without a circular struct definition.
#[derive(Debug, MemStruct)]
pub struct EntityReduced {
    #[offset(0x08)]
    pub type_: Pointer<EntityDBEntry>,
    #[offset(0x18)]
    pub items: EntityUidList,
    #[offset(0x38)]
    pub uid: u32,
    #[offset(0x40)]
    pub position_x: f32,
    #[offset(0x44)]
    pub position_y: f32,
    #[offset(0xA0)]
    pub layer: u8,
}

/// Full Entity: everything from EntityReduced plus an `overlay`
/// poly-pointer that lets callers see the entity this one is holding
/// / attached to.
#[derive(Debug, MemStruct)]
pub struct Entity {
    #[offset(0x08)]
    pub type_: Pointer<EntityDBEntry>,
    #[offset(0x10)]
    pub overlay: PolyPointer<EntityReduced>,
    #[offset(0x18)]
    pub items: EntityUidList,
    #[offset(0x38)]
    pub uid: u32,
    #[offset(0x40)]
    pub position_x: f32,
    #[offset(0x44)]
    pub position_y: f32,
    #[offset(0xA0)]
    pub layer: u8,
}

/// Movable = Entity + physics + character state. Everything mounts /
/// players / monsters inherit from.
#[derive(Debug, MemStruct)]
pub struct Movable {
    #[offset(0x08)]
    pub type_: Pointer<EntityDBEntry>,
    #[offset(0x10)]
    pub overlay: PolyPointer<EntityReduced>,
    #[offset(0x18)]
    pub items: EntityUidList,
    #[offset(0x38)]
    pub uid: u32,
    #[offset(0x40)]
    pub position_x: f32,
    #[offset(0x44)]
    pub position_y: f32,
    #[offset(0xA0)]
    pub layer: u8,
    #[offset(0x100)]
    pub idle_counter: u32,
    #[offset(0x108)]
    pub velocity_x: f32,
    #[offset(0x10C)]
    pub velocity_y: f32,
    /// UID of the entity this movable is holding, or -1 when empty.
    #[offset(0x110)]
    pub holding_uid: i32,
    #[offset(0x114)]
    pub state: CharState,
    #[offset(0x115)]
    pub last_state: CharState,
    #[offset(0x117)]
    pub health: i8,
}

/// A tamed mount. Only new field vs Movable is `is_tamed`; used to
/// pick out ridable mounts vs untamed ones for the Low% chain.
#[derive(Debug, MemStruct)]
pub struct Mount {
    #[offset(0x08)]
    pub type_: Pointer<EntityDBEntry>,
    #[offset(0x10)]
    pub overlay: PolyPointer<EntityReduced>,
    #[offset(0x18)]
    pub items: EntityUidList,
    #[offset(0x38)]
    pub uid: u32,
    #[offset(0x40)]
    pub position_x: f32,
    #[offset(0x44)]
    pub position_y: f32,
    #[offset(0xA0)]
    pub layer: u8,
    #[offset(0x100)]
    pub idle_counter: u32,
    #[offset(0x108)]
    pub velocity_x: f32,
    #[offset(0x10C)]
    pub velocity_y: f32,
    #[offset(0x110)]
    pub holding_uid: i32,
    #[offset(0x114)]
    pub state: CharState,
    #[offset(0x115)]
    pub last_state: CharState,
    #[offset(0x117)]
    pub health: i8,
    #[offset(0x151)]
    pub is_tamed: bool,
}

/// Player inventory. The `collected_money` array is 512 wide and holds
/// EntityType IDs (game encodes gem colours by which slot is nonzero);
/// only the first hundred-ish slots see nonzero values in a normal
/// run.
#[derive(Debug, MemStruct)]
pub struct Inventory {
    /// Money picked up on the current level. Resets on transition.
    #[offset(0x00)]
    pub money: u32,
    #[offset(0x04)]
    pub bombs: u8,
    #[offset(0x05)]
    pub ropes: u8,
    #[offset(0x06)]
    pub poison_tick_timer: i16,
    #[offset(0x08)]
    pub cursed: bool,
    /// Layout is `[EntityType; 512]` on the wire; held as u32s so the
    /// tracker can hash them without paying for u32 -> EntityType lift
    /// on every entry (many slots are 0).
    #[offset(0x20)]
    pub collected_money: [u32; 512],
    #[offset(0x1424)]
    pub kills_level: u32,
    #[offset(0x1428)]
    pub kills_total: u32,
    #[offset(0x1520)]
    pub collected_money_total: u32,
}

/// Manual Inventory element size because a `#[derive(MemLayout)]`-emitted
/// SIZE currently reads `max(offset + FieldType::SIZE)` and stops at
/// 0x1520 + 4 = 0x1524. The struct is 5412 bytes on the wire
/// (0x1524 rounded to alignment); use that here so arrays of Inventory
/// stride at the right cadence.
impl Inventory {
    pub const IN_MEMORY_SIZE: usize = 5412;
}

// Compile-time pins for the two hand-written struct sizes
// (`EntityDBEntry` = 256, `Inventory` = 5412). If a future offset edit
// drifts either constant, the derive-driven `MemLayout::SIZE` can
// still land past the fixed on-wire cadence; catch that here so
// arrays of these structs (Inventory in Items, EntityDBEntry table)
// never silently stride wrong.
const _: () = assert!(
    EntityDBEntry::IN_MEMORY_SIZE == 256,
    "EntityDBEntry must be 256 bytes on the wire"
);
const _: () = assert!(
    Inventory::IN_MEMORY_SIZE == 5412,
    "Inventory must be 5412 bytes on the wire"
);
const _: () = assert!(
    <Inventory as ml2_mem::MemLayout>::SIZE <= Inventory::IN_MEMORY_SIZE,
    "MemLayout::SIZE overran the 5412-byte fixed on-wire size"
);

/// The four-player container hanging off `State::items`. Layout:
/// pointers to the four Player entities (some or all may be null for
/// solo runs), then four inline Inventory structs.
///
/// `player_inventory` is inline (not pointers) so it's a big embedded
/// array; total struct size = 0x28 + 4 * Inventory::SIZE ~ 21728 bytes.
#[derive(Debug, MemStruct)]
pub struct Items {
    #[offset(0x08)]
    pub players: [Pointer<Player>; 4],
    #[offset(0x28)]
    pub player_inventory: [Inventory; 4],
}

#[derive(Debug, MemStruct)]
pub struct Player {
    #[offset(0x08)]
    pub type_: Pointer<EntityDBEntry>,
    #[offset(0x10)]
    pub overlay: PolyPointer<EntityReduced>,
    #[offset(0x18)]
    pub items: EntityUidList,
    #[offset(0x38)]
    pub uid: u32,
    #[offset(0x40)]
    pub position_x: f32,
    #[offset(0x44)]
    pub position_y: f32,
    #[offset(0xA0)]
    pub layer: u8,
    #[offset(0x100)]
    pub idle_counter: u32,
    #[offset(0x108)]
    pub velocity_x: f32,
    #[offset(0x10C)]
    pub velocity_y: f32,
    #[offset(0x110)]
    pub holding_uid: i32,
    #[offset(0x114)]
    pub state: CharState,
    #[offset(0x115)]
    pub last_state: CharState,
    #[offset(0x117)]
    pub health: i8,
    #[offset(0x140)]
    pub inventory: Pointer<Inventory>,
    /// UID of the next companion in the "who's linked to whom" chain
    /// used by the Low% chain to walk pet ownership.
    #[offset(0x150)]
    pub linked_companion_child: i32,
    #[offset(0x154)]
    pub linked_companion_parent: i32,
}

/// A light source's target position in world space. Trackers use this
/// for spotlight-based mechanics (Duat entrance, etc).
#[derive(Debug, MemStruct)]
pub struct Illumination {
    #[offset(0x48)]
    pub light_pos_x: f32,
    #[offset(0x4C)]
    pub light_pos_y: f32,
}

/// Movable that emits light. Currently unused by trackers, kept
/// because it's cheap and useful for future bookskip-style trackers.
#[derive(Debug, MemStruct)]
pub struct LightEmitter {
    #[offset(0x08)]
    pub type_: Pointer<EntityDBEntry>,
    #[offset(0x10)]
    pub overlay: PolyPointer<EntityReduced>,
    #[offset(0x18)]
    pub items: EntityUidList,
    #[offset(0x38)]
    pub uid: u32,
    #[offset(0x40)]
    pub position_x: f32,
    #[offset(0x44)]
    pub position_y: f32,
    #[offset(0xA0)]
    pub layer: u8,
    #[offset(0x100)]
    pub idle_counter: u32,
    #[offset(0x108)]
    pub velocity_x: f32,
    #[offset(0x10C)]
    pub velocity_y: f32,
    #[offset(0x110)]
    pub holding_uid: i32,
    #[offset(0x114)]
    pub state: CharState,
    #[offset(0x115)]
    pub last_state: CharState,
    #[offset(0x117)]
    pub health: i8,
    #[offset(0x130)]
    pub emitted_light: Pointer<Illumination>,
}

// ---------------------------------------------------------------------
// Tracker-relevant entity sets
// ---------------------------------------------------------------------
//
// Each set is a `&[EntityType]` literal so lookups are
// `slice.contains(&needle)`, which is O(N) but N is < 20 for every set
// and cache-friendly. If any set grows big enough to matter, promote
// to a static `HashSet` behind a `Lazy` initializer.

use crate::entity_types as et;

pub const MOUNTS: &[EntityType] = &[
    et::MOUNT_TURKEY,
    et::MOUNT_ROCKDOG,
    et::MOUNT_AXOLOTL,
    et::MOUNT_MECH,
    et::MOUNT_QILIN,
];

pub const BACKPACKS: &[EntityType] = &[
    et::ITEM_CAPE,
    et::ITEM_VLADS_CAPE,
    et::ITEM_HOVERPACK,
    et::ITEM_JETPACK,
    et::ITEM_POWERPACK,
    et::ITEM_TELEPORTER_BACKPACK,
];

/// Items disallowed by Low% attackable rules (attack-only weapons that
/// would count against the "no combat" spirit of Low%). Per-entity
/// exceptions live in the trailing comments below.
pub const LOW_BANNED_ATTACKABLES: &[EntityType] = &[
    et::ITEM_WEBGUN,
    et::ITEM_SHOTGUN,
    et::ITEM_FREEZERAY,
    et::ITEM_CLONEGUN,
    et::ITEM_CAMERA,
    et::ITEM_TELEPORTER,
    et::ITEM_BOOMERANG,
    et::ITEM_MACHETE,
    et::ITEM_BROKENEXCALIBUR,
    et::ITEM_PLASMACANNON,
    et::ITEM_LIGHT_ARROW,
    et::ITEM_CROSSBOW,
    // Allowed in moon challenge, sun challenge, waddler's lair, once
    // on Hundun with arrow of light.
    et::ITEM_HOUYIBOW,
    // Allowed in Abzu.
    et::ITEM_EXCALIBUR,
    // Allowed in moon challenge.
    et::ITEM_MATTOCK,
];

pub const LOW_BANNED_THROWABLES: &[EntityType] = &[];

pub const SHIELDS: &[EntityType] = &[et::ITEM_METAL_SHIELD, et::ITEM_WOODEN_SHIELD];

pub const TELEPORT_ENTITIES: &[EntityType] = &[
    et::ITEM_TELEPORTER,
    et::ITEM_TELEPORTER_BACKPACK,
    et::ITEM_POWERUP_TRUECROWN,
];

pub const CHAIN_POWERUP_ENTITIES: &[EntityType] = &[
    et::ITEM_POWERUP_UDJATEYE,
    et::ITEM_POWERUP_CROWN,
    et::ITEM_POWERUP_HEDJET,
    et::ITEM_POWERUP_ANKH,
    et::ITEM_POWERUP_TABLETOFDESTINY,
];

pub const NON_CHAIN_POWERUP_ENTITIES: &[EntityType] = &[
    et::ITEM_POWERUP_CLIMBING_GLOVES,
    et::ITEM_POWERUP_COMPASS,
    // Eggplant crown intentionally omitted: having the crown is a
    // valid modifier to every category, so its presence doesn't
    // disqualify Low%.
    et::ITEM_POWERUP_KAPALA,
    et::ITEM_POWERUP_PARACHUTE,
    et::ITEM_POWERUP_PASTE,
    et::ITEM_POWERUP_PITCHERSMITT,
    et::ITEM_POWERUP_SKELETON_KEY,
    et::ITEM_POWERUP_SPECIALCOMPASS,
    et::ITEM_POWERUP_SPECTACLES,
    et::ITEM_POWERUP_SPIKE_SHOES,
    et::ITEM_POWERUP_SPRING_SHOES,
    et::ITEM_POWERUP_TRUECROWN,
];

pub const GEMS: &[EntityType] = &[
    et::ITEM_RUBY,
    et::ITEM_EMERALD,
    et::ITEM_SAPPHIRE,
    et::ITEM_DIAMOND,
];

pub const DIAMOND: EntityType = et::ITEM_DIAMOND;
