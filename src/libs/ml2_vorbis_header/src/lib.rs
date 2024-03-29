use std::collections::HashMap;

use lazy_static::lazy_static;

lazy_static! {
    pub static ref LOOKUP: HashMap<u32, &'static [u8]> = {
        let mut lookup: HashMap<u32, &'static [u8]> = HashMap::new();

        lookup.insert(1461483860, include_bytes!("../data/crc32/1461483860"));
        lookup.insert(3196249009, include_bytes!("../data/crc32/3196249009"));

        lookup
    };
}
