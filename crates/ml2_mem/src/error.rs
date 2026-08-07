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
    /// The game is running but the OS refused access to it. Distinct from
    /// `NotAttached` because the fix is different. On Linux this is likely
    /// `kernel.yama.ptrace_scope`.
    #[error("cannot read process {pid}: {msg}")]
    AccessDenied { pid: u32, msg: String },
    #[error("feedcode not found; game may still be loading")]
    FeedcodeMissing,
    #[error("process reading not supported on this platform")]
    Unsupported,
}

pub type Result<T> = std::result::Result<T, MemError>;
