use thiserror::Error;

#[derive(Debug, Error)]
pub enum MemError {
    #[error("read at {addr:#x}: {msg}")]
    Read { addr: u64, msg: String },
    #[error("bad enum value {value} for {ty}")]
    BadEnum { ty: &'static str, value: i64 },
    #[error("null pointer at {addr:#x}")]
    NullPointer { addr: u64 },
    #[error("process not attached")]
    NotAttached,
    #[error("feedcode not found; game may still be loading")]
    FeedcodeMissing,
    #[error("process reading not supported on this platform")]
    Unsupported,
}

pub type Result<T> = std::result::Result<T, MemError>;
