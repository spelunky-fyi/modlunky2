//! Sprite merger: composes chunks from one or more loaders into a single
//! output PNG, plus an optional grid-hint PNG that visualizes the target
//! bounding boxes.
//!
//! Walks `origin_map` in order: for each loader, looks up each chunk name in
//! the matching loader's chunk map, crops the source region, and pastes it at
//! the target coordinates in a new RGBA image. Output size is the union of
//! the target regions, stacked vertically via a running height offset.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use image::codecs::png::{CompressionType, FilterType, PngEncoder};
use image::{ColorType, ImageEncoder, Rgba, RgbaImage, imageops};
use serde::Deserialize;

use crate::chunks::ChunkMap;
use crate::error::Result;
use crate::loader::SpriteLoader;

/// One entry in the merger's origin walk: which loader (by `name`, matching a
/// `LoaderConfig.name`) and which chunks to place, keyed by their name in
/// the loader's source chunk map, with target coordinates in the output.
#[derive(Debug, Clone, Deserialize)]
pub struct OriginEntry {
    pub loader_name: String,
    pub target_chunks: ChunkMap,
}

/// Merger config: the output PNG path (under `base_path`) and the ordered
/// list of loader references.
#[derive(Debug, Clone, Deserialize)]
pub struct MergerConfig {
    pub target_sprite_sheet_path: PathBuf,
    #[serde(default = "default_grid_hint_size")]
    pub grid_hint_size: u32,
    pub origin_map: Vec<OriginEntry>,
}

fn default_grid_hint_size() -> u32 {
    8
}

/// Result of a single merge: the composited RGBA image plus the sibling grid
/// hint image. Callers save these to disk with `save`.
pub struct MergeResult {
    pub sheet: RgbaImage,
    pub grid: RgbaImage,
    pub target_path: PathBuf,
}

impl MergeResult {
    /// Writes the sheet to `<base_path>/<target_sprite_sheet_path>` and the
    /// grid image next to it with `_grid` suffix, creating parent dirs as
    /// needed. Uses max PNG compression so output size stays reasonable; the
    /// `image` crate's default deflate level produces PNGs roughly 2x larger
    /// for the same pixel data.
    pub fn save(&self, base_path: &Path) -> Result<()> {
        let full = base_path.join(&self.target_path);
        if let Some(parent) = full.parent() {
            std::fs::create_dir_all(parent)?;
        }
        save_png_max_compression(&self.sheet, &full)?;
        let mut grid_path = full.clone();
        let stem = full.file_stem().and_then(|s| s.to_str()).unwrap_or("sheet");
        let ext = full.extension().and_then(|s| s.to_str()).unwrap_or("png");
        grid_path.set_file_name(format!("{stem}_grid.{ext}"));
        save_png_max_compression(&self.grid, &grid_path)?;
        Ok(())
    }
}

fn save_png_max_compression(image: &RgbaImage, path: &Path) -> Result<()> {
    let file = std::fs::File::create(path)?;
    let writer = std::io::BufWriter::new(file);
    let encoder = PngEncoder::new_with_quality(writer, CompressionType::Best, FilterType::Adaptive);
    encoder.write_image(
        image.as_raw(),
        image.width(),
        image.height(),
        ColorType::Rgba8.into(),
    )?;
    Ok(())
}

pub struct SpriteMerger {
    pub config: MergerConfig,
}

impl SpriteMerger {
    pub fn new(config: MergerConfig) -> Self {
        Self { config }
    }

    /// Composes the output image by walking origin_map. `loaders` is a lookup
    /// from loader name to loaded sheet; loaders referenced by the merger but
    /// missing from the map cause an error (unless `strict = false`, in which
    /// case they're skipped). Grid colors alternate red/blue in a checkerboard
    /// so tightly-packed chunks are visually separated.
    pub fn merge(
        &self,
        loaders: &HashMap<String, &SpriteLoader>,
        strict: bool,
    ) -> Result<MergeResult> {
        // First pass: compute the total image dimensions by summing entry
        // heights (each entry stacks below the previous) and taking the max
        // width.
        let mut total_height: u32 = 0;
        let mut max_width: u32 = 0;
        let mut entry_meta: Vec<(u32, u32, u32)> = Vec::new(); // (chunk_size, entry_width, entry_height)

        for entry in &self.config.origin_map {
            let Some(loader) = loaders.get(&entry.loader_name) else {
                if strict {
                    return Err(crate::SpriteError::MissingLoader(entry.loader_name.clone()));
                }
                entry_meta.push((0, 0, 0));
                continue;
            };
            let chunk_size = loader.chunk_size();
            let (w, h) = entry
                .target_chunks
                .values()
                .fold((0.0f32, 0.0f32), |(w, h), c| (w.max(c.2), h.max(c.3)));
            let ew = (w * chunk_size as f32) as u32;
            let eh = (h * chunk_size as f32) as u32;
            max_width = max_width.max(ew);
            total_height = total_height.saturating_add(eh);
            entry_meta.push((chunk_size, ew, eh));
        }

        // Zero-sized merger config (e.g. Ghost's empty-map entries) still
        // produces a 1x1 image so save() can write something; a well-formed
        // empty output is preferred to an error.
        let image_w = max_width.max(1);
        let image_h = total_height.max(1);
        let mut sheet = RgbaImage::from_pixel(image_w, image_h, Rgba([0, 0, 0, 0]));
        let mut grid = RgbaImage::from_pixel(image_w, image_h, Rgba([0, 0, 0, 0]));

        let mut height_offset: i32 = 0;
        for (entry, (chunk_size, _ew, eh)) in self.config.origin_map.iter().zip(entry_meta.iter()) {
            let Some(loader) = loaders.get(&entry.loader_name) else {
                continue;
            };
            let cs = *chunk_size;
            for (name, target) in &entry.target_chunks {
                let Some(source) = loader.get(name) else {
                    // Missing source chunk: skip rather than error, for leniency.
                    continue;
                };
                let tx = (target.0 * cs as f32) as i32;
                let ty = (target.1 * cs as f32) as i32 + height_offset;
                let tw = ((target.2 - target.0) * cs as f32) as u32;
                let th = ((target.3 - target.1) * cs as f32) as u32;
                // Use `replace` (direct pixel copy) instead of `overlay` so
                // transparency in source chunks isn't alpha-blended against
                // the destination.
                imageops::replace(&mut sheet, &source, tx as i64, ty as i64);
                draw_grid_rect(
                    &mut grid,
                    tx,
                    ty,
                    tw,
                    th,
                    self.config.grid_hint_size,
                    grid_color_for(tx, ty, cs),
                );
            }
            height_offset = height_offset.saturating_add(*eh as i32);
        }

        Ok(MergeResult {
            sheet,
            grid,
            target_path: self.config.target_sprite_sheet_path.clone(),
        })
    }
}

fn grid_color_for(tx: i32, ty: i32, chunk_size: u32) -> Rgba<u8> {
    // Checkerboard: red at even, blue at odd, offset by row.
    let chunk_x = tx.div_euclid(chunk_size as i32);
    let chunk_y = ty.div_euclid(chunk_size as i32);
    let mut idx = chunk_x.rem_euclid(2);
    if chunk_y.rem_euclid(2) != 0 {
        idx = 1 - idx;
    }
    if idx == 0 {
        Rgba([255, 0, 0, 255])
    } else {
        Rgba([0, 0, 255, 255])
    }
}

fn draw_grid_rect(
    dest: &mut RgbaImage,
    x: i32,
    y: i32,
    w: u32,
    h: u32,
    thickness: u32,
    color: Rgba<u8>,
) {
    if w == 0 || h == 0 {
        return;
    }
    let (dw, dh) = dest.dimensions();
    let x_end = (x + w as i32) - 1;
    let y_end = (y + h as i32) - 1;
    for t in 0..thickness as i32 {
        // Top and bottom edges.
        for dx in x..=x_end {
            if dx < 0 || dx >= dw as i32 {
                continue;
            }
            let top = y + t;
            let bot = y_end - t;
            if (0..dh as i32).contains(&top) {
                *dest.get_pixel_mut(dx as u32, top as u32) = color;
            }
            if (0..dh as i32).contains(&bot) {
                *dest.get_pixel_mut(dx as u32, bot as u32) = color;
            }
        }
        // Left and right edges.
        for dy in y..=y_end {
            if dy < 0 || dy >= dh as i32 {
                continue;
            }
            let left = x + t;
            let right = x_end - t;
            if (0..dw as i32).contains(&left) {
                *dest.get_pixel_mut(left as u32, dy as u32) = color;
            }
            if (0..dw as i32).contains(&right) {
                *dest.get_pixel_mut(right as u32, dy as u32) = color;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::chunks::ChunkCoords;
    use crate::loader::LoaderConfig;
    use std::collections::BTreeMap;
    use tempfile::TempDir;

    fn write_solid_png(path: &Path, w: u32, h: u32, color: Rgba<u8>) {
        let img = RgbaImage::from_pixel(w, h, color);
        img.save(path).unwrap();
    }

    fn make_test_loader(name: &str, sheet_path: PathBuf, chunk_size: u32) -> LoaderConfig {
        let mut chunk_map = BTreeMap::new();
        chunk_map.insert("chunk_a".to_string(), ChunkCoords(0.0, 0.0, 1.0, 1.0));
        chunk_map.insert("chunk_b".to_string(), ChunkCoords(1.0, 0.0, 2.0, 1.0));
        LoaderConfig {
            name: name.to_string(),
            sprite_sheet_path: sheet_path,
            chunk_size,
            chunk_map,
        }
    }

    #[test]
    fn merge_two_chunks_into_output() {
        let dir = TempDir::new().unwrap();
        let base = dir.path().to_path_buf();
        std::fs::create_dir_all(base.join("Data/Textures")).unwrap();

        // Source sheet: 2 chunks wide, 1 tall, chunk_size 8 pixels.
        // Left chunk = solid red, right chunk = solid green.
        let sheet_path = base.join("Data/Textures/test.png");
        let mut sheet = RgbaImage::from_pixel(16, 8, Rgba([0, 0, 0, 0]));
        for y in 0..8 {
            for x in 0..8 {
                sheet.put_pixel(x, y, Rgba([255, 0, 0, 255]));
            }
            for x in 8..16 {
                sheet.put_pixel(x, y, Rgba([0, 255, 0, 255]));
            }
        }
        sheet.save(&sheet_path).unwrap();

        let loader_cfg = make_test_loader("TestSheet", PathBuf::from("Data/Textures/test.png"), 8);
        let loader = SpriteLoader::open(&base, loader_cfg).unwrap();

        // Merger takes chunk_a and chunk_b, places them stacked in a 1x2 grid.
        let mut targets = BTreeMap::new();
        targets.insert("chunk_a".to_string(), ChunkCoords(0.0, 0.0, 1.0, 1.0));
        targets.insert("chunk_b".to_string(), ChunkCoords(0.0, 1.0, 1.0, 2.0));

        let merger = SpriteMerger::new(MergerConfig {
            target_sprite_sheet_path: PathBuf::from("Data/Textures/Entities/test_out.png"),
            grid_hint_size: 1,
            origin_map: vec![OriginEntry {
                loader_name: "TestSheet".to_string(),
                target_chunks: targets,
            }],
        });

        let mut loaders = HashMap::new();
        loaders.insert("TestSheet".to_string(), &loader);

        let result = merger.merge(&loaders, true).unwrap();
        assert_eq!(result.sheet.dimensions(), (8, 16));
        // Top chunk pixel should be red, bottom green.
        assert_eq!(result.sheet.get_pixel(0, 0), &Rgba([255, 0, 0, 255]));
        assert_eq!(result.sheet.get_pixel(0, 8), &Rgba([0, 255, 0, 255]));

        // Save round trip works.
        result.save(&base).unwrap();
        assert!(base.join("Data/Textures/Entities/test_out.png").exists());
        assert!(
            base.join("Data/Textures/Entities/test_out_grid.png")
                .exists()
        );

        let _ = write_solid_png; // reference to silence dead-code warning
    }
}
