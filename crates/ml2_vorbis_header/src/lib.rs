use std::collections::HashMap;
use std::sync::LazyLock;

pub static LOOKUP: LazyLock<HashMap<u32, &'static [u8]>> = LazyLock::new(|| {
    let mut lookup: HashMap<u32, &'static [u8]> = HashMap::new();
    lookup.insert(1461483860, include_bytes!("../data/crc32/1461483860"));
    lookup.insert(3196249009, include_bytes!("../data/crc32/3196249009"));
    lookup
});
