//! Spelunky 2's per-entity children list.
//!
//! Every Entity carries a list of the entities it "owns" (held items,
//! attached powerups, mount rider, active-floor riders, etc). On the
//! wire this is NOT an `std::vector<uint32_t>`; the game uses a small
//! custom struct with two parallel arrays:
//!
//! ```text
//! struct EntityList {          // 24 bytes total
//!     Entity** ent_list;       // 0x00, pointer to Entity* array
//!     uint32_t* uid_list;      // 0x08, pointer to parallel UID array
//!     uint32_t  cap;           // 0x10, allocated slots
//!     uint32_t  size;          // 0x14, live count
//! };
//! ```
//!
//! Reading it as an MSVC `std::vector` (which is `first/last/capacity`
//! three pointers) misplaces both the base address and the length, so
//! callers get a random handful of pointer low-32-bits per element. The
//! Python port got this right via a custom `_VectorMeta { array_addr @
//! 0x08, size @ 0x14 }`; this mirrors that.
//!
//! Only the UIDs are surfaced. Callers that need the entity itself
//! resolve each UID through the game's `UidEntityMap`, which is already
//! the standard indirection for every other tracker lookup.

use crate::error::Result;
use crate::mem_type::{MemLayout, MemType};
use crate::process::{self, ReadProcess};

const ENTITY_LIST_SIZE: usize = 24;

#[derive(Debug, Clone, Copy)]
pub struct EntityUidList {
    /// Base of the UID array. 0 when the list has never been allocated
    /// (unspawned entity, torn read mid-frame).
    pub uid_list: u64,
    pub cap: u32,
    pub size: u32,
}

impl EntityUidList {
    pub fn is_null(&self) -> bool {
        self.uid_list == 0
    }

    pub fn len(&self) -> usize {
        self.size as usize
    }

    pub fn is_empty(&self) -> bool {
        self.size == 0
    }

    /// Read every UID in the list. Empty on null base or zero size.
    pub fn load(&self, process: &dyn ReadProcess) -> Result<Vec<u32>> {
        if self.is_null() || self.size == 0 {
            return Ok(Vec::new());
        }
        let mut out = Vec::with_capacity(self.size as usize);
        for i in 0..self.size as u64 {
            out.push(process::read_u32(process, self.uid_list + i * 4)?);
        }
        Ok(out)
    }
}

impl MemType for EntityUidList {
    fn read_from(process: &dyn ReadProcess, addr: u64) -> Result<Self> {
        Ok(Self {
            uid_list: process::read_u64(process, addr + 0x08)?,
            cap: process::read_u32(process, addr + 0x10)?,
            size: process::read_u32(process, addr + 0x14)?,
        })
    }
}

impl MemLayout for EntityUidList {
    const SIZE: usize = ENTITY_LIST_SIZE;
}
