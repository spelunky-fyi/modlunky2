use std::collections::HashMap;
use std::sync::LazyLock;

use ml2_types::Animation;
use ml2_types::Entity;
use ml2_types::RectCollision;
use ml2_types::Size;
use ml2_types::Texture;

pub static ENTITIES: LazyLock<HashMap<String, Entity>> =
    LazyLock::new(|| include!(concat!(env!("OUT_DIR"), "/entities.rs")));
pub static TEXTURES: LazyLock<HashMap<String, Texture>> =
    LazyLock::new(|| include!(concat!(env!("OUT_DIR"), "/textures.rs")));
