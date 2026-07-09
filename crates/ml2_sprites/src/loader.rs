//! Sprite loader: opens a source PNG and lets callers crop out named chunks
//! by consulting a `ChunkMap`. Generic and data-driven rather than one type
//! per sheet.

use std::path::{Path, PathBuf};

use image::{DynamicImage, GenericImageView, RgbaImage};
use serde::Deserialize;

use crate::chunks::{ChunkCoords, ChunkMap};
use crate::error::{Result, SpriteError};

/// Sheet metadata: the PNG's relative path, its chunk size, and the
/// name-to-coords mapping. Populated from generated Rust data at startup so
/// hundreds of per-sheet coordinate tables don't need hand-transcription.
#[derive(Debug, Clone, Deserialize)]
pub struct LoaderConfig {
    /// A stable name (e.g. `"ItemSheet"`) used as the key mergers use to
    /// reference this loader.
    pub name: String,
    /// Where to find the PNG under `base_path`.
    pub sprite_sheet_path: PathBuf,
    /// Pixels per chunk unit.
    pub chunk_size: u32,
    /// name -> chunk coords, in chunk units.
    pub chunk_map: ChunkMap,
}

/// Runtime loader: pairs a `LoaderConfig` with the actual loaded PNG so
/// `get()` can crop.
pub struct SpriteLoader {
    pub config: LoaderConfig,
    sheet: DynamicImage,
}

impl SpriteLoader {
    /// Opens the PNG at `base_path / config.sprite_sheet_path`. Errors out if
    /// the file is missing rather than skipping so callers know their extract
    /// dir is incomplete. Bubbles image decoding errors.
    pub fn open(base_path: &Path, config: LoaderConfig) -> Result<Self> {
        let full_path = base_path.join(&config.sprite_sheet_path);
        if !full_path.exists() {
            return Err(SpriteError::MissingSource(full_path.display().to_string()));
        }
        let sheet = image::open(&full_path)?;
        Ok(Self { config, sheet })
    }

    /// Same as `open` but tolerates a missing source PNG by returning None.
    /// Useful when running the full merger pipeline where some sheets may be
    /// absent (e.g. DLC-only textures on a base install).
    pub fn open_if_present(base_path: &Path, config: LoaderConfig) -> Result<Option<Self>> {
        let full_path = base_path.join(&config.sprite_sheet_path);
        if !full_path.exists() {
            return Ok(None);
        }
        let sheet = image::open(&full_path)?;
        Ok(Some(Self { config, sheet }))
    }

    pub fn name(&self) -> &str {
        &self.config.name
    }

    pub fn chunk_size(&self) -> u32 {
        self.config.chunk_size
    }

    /// Crops the chunk named `name` out of the source sheet. Returns None if
    /// the name isn't in the chunk map; the caller is expected to check and
    /// log.
    pub fn get(&self, name: &str) -> Option<RgbaImage> {
        let coords = self.config.chunk_map.get(name)?;
        Some(self.crop(*coords))
    }

    fn crop(&self, coords: ChunkCoords) -> RgbaImage {
        let cs = self.config.chunk_size as f32;
        let x = (coords.0 * cs) as u32;
        let y = (coords.1 * cs) as u32;
        let w = ((coords.2 - coords.0) * cs) as u32;
        let h = ((coords.3 - coords.1) * cs) as u32;
        self.sheet.view(x, y, w, h).to_image()
    }
}
