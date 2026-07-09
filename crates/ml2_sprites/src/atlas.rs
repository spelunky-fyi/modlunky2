//! Simple texture atlas builder.
//!
//! Takes a set of named RGBA sub-images and packs them into a single PNG
//! plus an index of `name -> UvRect` (in atlas pixels). The frontend uses
//! this to load one texture into PixiJS and render every tile via texture
//! sub-rects rather than one texture per tile.
//!
//! The packer is a naive shelf packer: sort inputs by height descending,
//! lay them out row-by-row with a fixed maximum width. Good enough for a
//! few hundred tiles per biome. If better packing is ever needed, swap in
//! `rectangle-pack` or `guillotiere`; the caller-visible API doesn't need
//! to change.

use std::io::Cursor;

use image::codecs::png::{CompressionType, FilterType, PngEncoder};
use image::{ColorType, ImageBuffer, ImageEncoder, Rgba, RgbaImage};
use serde::Serialize;

use crate::error::{Result, SpriteError};

/// A texture rectangle in atlas pixels. Frontend maps this to a PixiJS
/// `Rectangle` for a sub-texture.
#[derive(Debug, Clone, Copy, Serialize)]
pub struct UvRect {
    pub x: u32,
    pub y: u32,
    pub w: u32,
    pub h: u32,
}

/// One named input tile.
pub struct TileInput {
    pub name: String,
    pub image: RgbaImage,
}

/// The result of packing: a PNG blob and an ordered list of `(name, uv)`
/// pairs. Ordered so the frontend can preserve palette order if the caller
/// supplied one.
pub struct Atlas {
    pub png: Vec<u8>,
    pub tiles: Vec<(String, UvRect)>,
    pub width: u32,
    pub height: u32,
}

pub struct AtlasOptions {
    /// Max atlas width in pixels. Determines how many rows the shelf packer
    /// creates. Common GPU texture size ceilings: 2048, 4096, 8192.
    pub max_width: u32,
    /// Pixels of transparent margin between tiles. Prevents bleed when the
    /// atlas is scaled or filtered.
    pub padding: u32,
}

impl Default for AtlasOptions {
    fn default() -> Self {
        Self {
            max_width: 2048,
            padding: 2,
        }
    }
}

/// Build a texture atlas from `inputs`. Preserves the caller's tile order
/// in the returned index even though internal layout is height-sorted.
pub fn build_atlas(inputs: Vec<TileInput>, opts: AtlasOptions) -> Result<Atlas> {
    if inputs.is_empty() {
        return Err(SpriteError::EmptyMerger);
    }

    // Remember the caller's order so the returned tiles list matches.
    let order: Vec<String> = inputs.iter().map(|t| t.name.clone()).collect();

    // Sort a copy by descending height for the shelf packer.
    let mut sorted_indices: Vec<usize> = (0..inputs.len()).collect();
    sorted_indices.sort_by_key(|&i| std::cmp::Reverse(inputs[i].image.height()));

    let mut rects: Vec<(String, UvRect)> = Vec::with_capacity(inputs.len());
    // Track cursor position and shelf state.
    let mut cursor_x: u32 = opts.padding;
    let mut cursor_y: u32 = opts.padding;
    let mut shelf_height: u32 = 0;
    let mut total_width: u32 = 0;

    // First pass: compute placements without allocating the atlas image.
    let mut placements: Vec<UvRect> = vec![
        UvRect {
            x: 0,
            y: 0,
            w: 0,
            h: 0
        };
        inputs.len()
    ];
    for &idx in &sorted_indices {
        let (w, h) = inputs[idx].image.dimensions();
        if cursor_x + w + opts.padding > opts.max_width && cursor_x > opts.padding {
            // Wrap to next shelf.
            cursor_y += shelf_height + opts.padding;
            cursor_x = opts.padding;
            shelf_height = 0;
        }
        placements[idx] = UvRect {
            x: cursor_x,
            y: cursor_y,
            w,
            h,
        };
        cursor_x += w + opts.padding;
        shelf_height = shelf_height.max(h);
        total_width = total_width.max(cursor_x);
    }
    let total_height = cursor_y + shelf_height + opts.padding;

    // Allocate transparent atlas image.
    let mut atlas: RgbaImage =
        ImageBuffer::from_pixel(total_width, total_height, Rgba([0, 0, 0, 0]));

    // Second pass: blit each input at its placement.
    for (idx, input) in inputs.iter().enumerate() {
        let uv = placements[idx];
        image::imageops::replace(&mut atlas, &input.image, uv.x as i64, uv.y as i64);
    }

    // Rebuild the caller-ordered tile list.
    for name in order {
        let idx = inputs
            .iter()
            .position(|t| t.name == name)
            .expect("order derived from inputs");
        rects.push((name, placements[idx]));
    }

    // Encode PNG. Fast compression trades a modest size increase (~10-15%)
    // for a large speedup on this hot path: the atlas ships once over IPC
    // to the frontend where it lives in memory as a texture, so payload
    // size doesn't matter but encode latency directly hits the level-load
    // wall-clock.
    let mut png_bytes = Vec::new();
    {
        let mut cursor = Cursor::new(&mut png_bytes);
        let encoder =
            PngEncoder::new_with_quality(&mut cursor, CompressionType::Fast, FilterType::Adaptive);
        encoder.write_image(
            atlas.as_raw(),
            atlas.width(),
            atlas.height(),
            ColorType::Rgba8.into(),
        )?;
    }

    Ok(Atlas {
        png: png_bytes,
        tiles: rects,
        width: total_width,
        height: total_height,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn solid(w: u32, h: u32, color: [u8; 4]) -> RgbaImage {
        ImageBuffer::from_pixel(w, h, Rgba(color))
    }

    #[test]
    fn build_atlas_places_all_tiles() {
        let inputs = vec![
            TileInput {
                name: "a".into(),
                image: solid(128, 128, [255, 0, 0, 255]),
            },
            TileInput {
                name: "b".into(),
                image: solid(64, 64, [0, 255, 0, 255]),
            },
            TileInput {
                name: "c".into(),
                image: solid(32, 128, [0, 0, 255, 255]),
            },
        ];
        let atlas = build_atlas(
            inputs,
            AtlasOptions {
                max_width: 512,
                padding: 1,
            },
        )
        .unwrap();
        assert_eq!(atlas.tiles.len(), 3);
        assert_eq!(atlas.tiles[0].0, "a");
        assert_eq!(atlas.tiles[1].0, "b");
        assert_eq!(atlas.tiles[2].0, "c");
        assert!(atlas.width > 0);
        assert!(atlas.height > 0);
        assert!(!atlas.png.is_empty());
    }

    #[test]
    fn build_atlas_wraps_to_new_row() {
        let inputs: Vec<TileInput> = (0..20)
            .map(|i| TileInput {
                name: format!("t{i}"),
                image: solid(64, 64, [255, 255, 255, 255]),
            })
            .collect();
        let atlas = build_atlas(
            inputs,
            AtlasOptions {
                max_width: 200,
                padding: 0,
            },
        )
        .unwrap();
        assert!(
            atlas.height >= 128,
            "expected multiple rows, got h={}",
            atlas.height
        );
    }

    #[test]
    fn build_atlas_rejects_empty_input() {
        let err = build_atlas(vec![], AtlasOptions::default());
        assert!(err.is_err());
    }
}
