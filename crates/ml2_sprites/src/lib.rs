//! Sprite sheet splitter/merger for Spelunky 2 assets.
//!
//! Given an unpacked `Data/Textures/` directory from Spel2.exe, this crate
//! composes per-entity sheets under `Data/Textures/Entities/`. The engine
//! is data-driven: loader and merger configs live in generated Rust source
//! under `data/`, so hundreds of coordinate tables don't need
//! hand-transcription.

pub mod atlas;
mod chunks;
pub mod data;
mod error;
mod loader;
mod merger;

pub use atlas::{Atlas, AtlasOptions, TileInput, UvRect, build_atlas};
pub use chunks::{
    ChunkCoords, ChunkMap, EntitiesJson, EntityData, TextureData, TexturesJson,
    chunks_from_animation, chunks_from_json, target_chunks_from_json,
};
pub use data::{all_loaders, all_mergers};
pub use error::{Result, SpriteError};
pub use loader::{LoaderConfig, SpriteLoader};
pub use merger::{MergerConfig, OriginEntry, SpriteMerger};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generated_loaders_contain_item_sheet() {
        let configs = all_loaders();
        assert!(!configs.is_empty());
        let item_sheet = configs
            .iter()
            .find(|c| c.name == "ItemSheet")
            .expect("ItemSheet loader missing from generated data");
        assert_eq!(item_sheet.chunk_size, 128);
        assert!(item_sheet.chunk_map.contains_key("chest"));
    }

    #[test]
    fn generated_mergers_are_non_empty() {
        let configs = all_mergers();
        assert!(
            configs.len() > 100,
            "expected ~128 mergers, got {}",
            configs.len()
        );
    }
}
