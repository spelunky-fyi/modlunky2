use thiserror::Error;

#[derive(Error, Debug)]
pub enum LevelError {
    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("directive missing name: {0:?}")]
    MissingName(String),

    #[error("directive {0:?} missing value")]
    MissingValue(String),

    #[error("directive {name:?} has invalid value {value:?}: {reason}")]
    InvalidValue {
        name: String,
        value: String,
        reason: String,
    },

    #[error("chance value for {name:?} must be 1 or 4 ints, got {count}")]
    BadChanceLen { name: String, count: usize },

    #[error("tile code {name:?} value {value:?} must be exactly one character")]
    BadTileCodeLen { name: String, value: String },

    #[error("size directive expects two values, got {0}")]
    BadSize(usize),

    #[error("dmpreview.tok: {0}")]
    BadDmPreview(String),
}

pub type Result<T> = std::result::Result<T, LevelError>;
