//! The game's entity and texture tables, bundled with the binary.
//!
//! The two JSON files are embedded as static text and parsed into maps on
//! first use.

use std::collections::HashMap;
use std::sync::LazyLock;

use ml2_types::Entity;
use ml2_types::Texture;

/// Every `ENT_TYPE_*` the game knows, by name.
pub static ENTITIES: LazyLock<HashMap<String, Entity>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../data/entities.json"))
        .expect("bundled entities.json does not match ml2_types::Entity")
});

/// Every texture the game knows, by name.
pub static TEXTURES: LazyLock<HashMap<String, Texture>> = LazyLock::new(|| {
    serde_json::from_str(include_str!("../data/textures.json"))
        .expect("bundled textures.json does not match ml2_types::Texture")
});

#[cfg(test)]
mod tests {
    /// The bundled data used to be parsed by the build script, so a file
    /// that did not match the types broke the build. It is parsed on
    /// first use now, so this is what catches that instead.
    #[test]
    fn the_bundled_tables_parse() {
        assert!(!super::ENTITIES.is_empty());
        assert!(!super::TEXTURES.is_empty());
    }

    /// Parsing must not need a large stack: the app reaches these tables
    /// from Tauri command threads, which have far less than the main
    /// thread. This is the regression the parsing approach fixes.
    #[test]
    fn the_tables_build_on_a_small_stack() {
        std::thread::Builder::new()
            .stack_size(128 * 1024)
            .spawn(|| (super::ENTITIES.len(), super::TEXTURES.len()))
            .unwrap()
            .join()
            .unwrap();
    }
}
