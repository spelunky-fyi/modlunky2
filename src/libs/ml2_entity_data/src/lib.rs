use std::collections::HashMap;

use lazy_static::lazy_static;

use ml2_types::Animation;
use ml2_types::Entity;
use ml2_types::RectCollision;
use ml2_types::Size;
use ml2_types::Texture;

lazy_static! {
    pub static ref ENTITIES: HashMap<String, Entity> =
        include!(concat!(env!("OUT_DIR"), "/entities.rs"));
    pub static ref TEXTURES: HashMap<String, Texture> =
        include!(concat!(env!("OUT_DIR"), "/textures.rs"));
}
