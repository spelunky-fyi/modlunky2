use std::collections::HashMap;

use ml2_types::{Entity, Texture};

fn main() -> anyhow::Result<()> {
    let entities: HashMap<String, Entity> =
        serde_json::from_str(include_str!("data/entities.json"))?;

    uneval::to_out_dir(entities, "entities.rs")?;

    let textures: HashMap<String, Texture> =
        serde_json::from_str(include_str!("data/textures.json"))?;
    uneval::to_out_dir(textures, "textures.rs")?;
    Ok(())
}
