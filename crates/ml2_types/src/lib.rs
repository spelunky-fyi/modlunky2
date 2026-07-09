use std::collections::HashMap;

use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct RectCollision {
    pub masks: i64,
    pub side: f64,
    pub up_minus_down: f64,
    pub up_plus_down: f64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Animation {
    pub count: i64,
    pub interval: i64,
    pub key: i64,
    pub repeat: i64,
    pub texture: i64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Entity {
    pub acceleration: f64,
    pub animations: HashMap<String, Animation>,
    #[serde(rename(deserialize = "attachOffsetX"))]
    pub attach_offset_x: f64,
    #[serde(rename(deserialize = "attachOffsetY"))]
    pub attach_offset_y: f64,
    pub damage: i64,
    pub elasticity: f64,
    pub friction: f64,
    pub height: f64,
    pub id: i64,
    pub jump: f64,
    pub life: i64,
    pub max_speed: f64,
    pub rect_collision: RectCollision,
    pub search_flags: i64,
    pub sprint_factor: f64,
    pub technique: i64,
    pub texture: i64,
    pub tile_x: i64,
    pub tile_y: i64,
    pub weight: f64,
    pub width: f64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Size {
    pub height: i64,
    pub width: i64,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct Texture {
    pub height: i64,
    pub width: i64,
    pub num_tiles: Size,
    pub offset: Size,
    pub path: String,
    pub tile_height: i64,
    pub tile_width: i64,
}
