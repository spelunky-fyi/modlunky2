use thiserror::Error;

#[derive(Error, Debug)]
pub enum SpriteError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Image error: {0}")]
    Image(#[from] image::ImageError),

    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    #[error("Missing source PNG at {0}")]
    MissingSource(String),

    #[error("Missing chunk {name:?} in loader {loader:?}")]
    MissingChunk { loader: String, name: String },

    #[error("Missing loader {0:?} referenced by merger")]
    MissingLoader(String),

    #[error("Merger produced empty output image")]
    EmptyMerger,

    #[error("Unknown entity {0:?} not in entities.json")]
    UnknownEntity(String),

    #[error("Unknown texture id {0:?} not in textures.json")]
    UnknownTexture(String),
}

pub type Result<T> = std::result::Result<T, SpriteError>;
