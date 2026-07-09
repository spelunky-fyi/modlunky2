//! Chunk math shared by loaders and mergers, plus the entities.json and
//! textures.json schema.
//!
//! Chunk coordinates are expressed as `(left, upper, right, lower)` in
//! *chunk units*, where the actual pixel bounding box is obtained by
//! multiplying by the loader's `chunk_size`. `f32` (rather than integers)
//! because entries generated from textures.json can span fractional chunk
//! sizes when a sheet uses a different tile size than its owner declares.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use crate::SpriteError;

/// (left, upper, right, lower) in chunk units.
#[derive(Copy, Clone, Debug, Deserialize, Serialize, PartialEq)]
pub struct ChunkCoords(pub f32, pub f32, pub f32, pub f32);

impl ChunkCoords {
    pub fn width(&self) -> f32 {
        self.2 - self.0
    }

    pub fn height(&self) -> f32 {
        self.3 - self.1
    }
}

impl From<(f32, f32, f32, f32)> for ChunkCoords {
    fn from((l, u, r, low): (f32, f32, f32, f32)) -> Self {
        Self(l, u, r, low)
    }
}

impl From<(i32, i32, i32, i32)> for ChunkCoords {
    fn from((l, u, r, low): (i32, i32, i32, i32)) -> Self {
        Self(l as f32, u as f32, r as f32, low as f32)
    }
}

/// Ordered map of chunk name to its coordinates within a source sheet. Ordered
/// so that a merger walks entries in a stable order.
pub type ChunkMap = BTreeMap<String, ChunkCoords>;

/// Given a starting chunk and a count, produce sequentially named animation
/// frames offset horizontally by the starting chunk's width.
pub fn chunks_from_animation(
    base_name: &str,
    start: ChunkCoords,
    num_chunks: u32,
    off: u32,
) -> ChunkMap {
    let mut out = ChunkMap::new();
    let chunk_width = start.width();
    for i in 0..num_chunks {
        let offset = i as f32 * chunk_width;
        out.insert(
            format!("{base_name}_{}", off + i + 1),
            ChunkCoords(start.0 + offset, start.1, start.2 + offset, start.3),
        );
    }
    out
}

/// `entities.json` and `textures.json` schemas. Only the fields consumed by
/// `chunks_from_json` are deserialized; unknown keys are ignored.

#[derive(Debug, Deserialize)]
#[serde(transparent)]
pub struct EntitiesJson(pub std::collections::HashMap<String, EntityData>);

#[derive(Debug, Deserialize)]
pub struct EntityData {
    pub texture: i64,
    #[serde(default)]
    pub tile_x: i64,
    #[serde(default)]
    pub tile_y: i64,
    #[serde(default)]
    pub animations: std::collections::HashMap<String, EntityAnimation>,
}

#[derive(Debug, Deserialize)]
pub struct EntityAnimation {
    pub texture: i64,
    pub count: i64,
}

#[derive(Debug, Deserialize)]
#[serde(transparent)]
pub struct TexturesJson(pub std::collections::HashMap<String, TextureData>);

#[derive(Debug, Deserialize)]
pub struct TextureData {
    pub num_tiles: TextureTiles,
    pub offset: TextureOffset,
    pub tile_width: f32,
    pub tile_height: f32,
}

#[derive(Debug, Deserialize)]
pub struct TextureTiles {
    pub width: i64,
}

#[derive(Debug, Deserialize)]
pub struct TextureOffset {
    pub width: f32,
    pub height: f32,
}

/// Turns an entity from entities.json into a chunk map keyed by
/// `<entity>_<animation>_<frame_idx>`.
pub fn chunks_from_json(
    entities: &EntitiesJson,
    textures: &TexturesJson,
    entity_name: &str,
    chunk_size: u32,
) -> Result<ChunkMap, SpriteError> {
    let entity = entities
        .0
        .get(entity_name)
        .ok_or_else(|| SpriteError::UnknownEntity(entity_name.to_string()))?;
    let texture_id = entity.texture.to_string();
    let texture = textures
        .0
        .get(&texture_id)
        .ok_or_else(|| SpriteError::UnknownTexture(texture_id))?;

    let num_chunks_width = texture.num_tiles.width;
    let chunk_size_f = chunk_size as f32;
    let offset_width = texture.offset.width / chunk_size_f;
    let offset_height = texture.offset.height / chunk_size_f;
    let chunk_width_scaling = texture.tile_width / chunk_size_f;
    let chunk_height_scaling = texture.tile_height / chunk_size_f;

    // Sort animations by numeric key so the output order is deterministic.
    let mut animations: Vec<(String, EntityAnimationRef)> = if entity.animations.is_empty() {
        // No animations declared: treat tile_x/tile_y as a single frame.
        vec![(
            "0".to_string(),
            EntityAnimationRef {
                texture: entity.tile_y * num_chunks_width + entity.tile_x,
                count: 1,
            },
        )]
    } else {
        entity
            .animations
            .iter()
            .map(|(k, v)| {
                (
                    k.clone(),
                    EntityAnimationRef {
                        texture: v.texture,
                        count: v.count,
                    },
                )
            })
            .collect()
    };
    animations.sort_by_key(|(k, _)| k.parse::<i64>().unwrap_or(0));

    let mut out = ChunkMap::new();
    for (animation_id, animation) in animations {
        let first_chunk = animation.texture;
        for i in 0..animation.count {
            let chunk_x = ((first_chunk + i) % num_chunks_width) as f32;
            let chunk_y = ((first_chunk + i) / num_chunks_width) as f32;
            out.insert(
                format!("{entity_name}_{animation_id}_{i}"),
                ChunkCoords(
                    offset_width + chunk_x * chunk_width_scaling,
                    offset_height + chunk_y * chunk_height_scaling,
                    offset_width + (chunk_x + 1.0) * chunk_width_scaling,
                    offset_height + (chunk_y + 1.0) * chunk_height_scaling,
                ),
            );
        }
    }
    Ok(out)
}

struct EntityAnimationRef {
    texture: i64,
    count: i64,
}

/// Where to *place* each entity chunk in the merged output image. Packs
/// unique chunks in a roughly-square grid, sized to the max chunk width and
/// height across the entity.
pub fn target_chunks_from_json(
    entities: &EntitiesJson,
    textures: &TexturesJson,
    entity_name: &str,
    chunk_size: u32,
) -> Result<ChunkMap, SpriteError> {
    let chunks = chunks_from_json(entities, textures, entity_name, chunk_size)?;

    // Deduplicate by coordinates while preserving the first occurrence.
    let mut unique: Vec<(String, ChunkCoords)> = Vec::with_capacity(chunks.len());
    for (name, coords) in &chunks {
        if !unique.iter().any(|(_, c)| c == coords) {
            unique.push((name.clone(), *coords));
        }
    }

    let (max_w, max_h) = unique.iter().fold((0.0f32, 0.0f32), |(w, h), (_, c)| {
        (w.max(c.width()), h.max(c.height()))
    });
    let num_cols = (unique.len() as f32).sqrt().ceil() as usize;

    let mut out = ChunkMap::new();
    for (i, (name, coords)) in unique.into_iter().enumerate() {
        let col = (i % num_cols) as f32;
        let row = (i / num_cols) as f32;
        let to_x = col * max_w;
        let to_y = row * max_h;
        out.insert(
            name,
            ChunkCoords(to_x, to_y, to_x + coords.width(), to_y + coords.height()),
        );
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn animation_chunks_offset_by_width() {
        let m = chunks_from_animation("attack", ChunkCoords(0.0, 0.0, 1.0, 1.0), 3, 0);
        assert_eq!(m.get("attack_1"), Some(&ChunkCoords(0.0, 0.0, 1.0, 1.0)));
        assert_eq!(m.get("attack_2"), Some(&ChunkCoords(1.0, 0.0, 2.0, 1.0)));
        assert_eq!(m.get("attack_3"), Some(&ChunkCoords(2.0, 0.0, 3.0, 1.0)));
    }

    #[test]
    fn animation_chunks_honor_off() {
        let m = chunks_from_animation("idle", ChunkCoords(2.0, 1.0, 3.0, 2.0), 2, 5);
        assert!(m.contains_key("idle_6"));
        assert!(m.contains_key("idle_7"));
    }
}
