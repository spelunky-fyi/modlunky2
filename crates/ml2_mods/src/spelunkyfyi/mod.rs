use reqwest::StatusCode;
use reqwest::header::InvalidHeaderValue;

pub mod demo;
pub mod http;
pub mod web_socket;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("Invalid URI: {0:?}")]
    InvalidUri(#[from] anyhow::Error),
    #[error("Invalid auth token")]
    InvalidToken(#[from] InvalidHeaderValue),

    #[error("HTTP status: {0:?}")]
    StatusError(StatusCode),
    #[error("HTTP error: {0:?}")]
    GenericHttpError(#[source] anyhow::Error),

    #[error("I/O error: {0:?}")]
    IoError(#[from] std::io::Error),
    #[error("JSON error: {0:?}")]
    JsonError(#[from] serde_json::Error),
    /// Boxed to keep `Error` small: `tungstenite::Error` on its own is
    /// ~136 bytes and would blow up every `Result<T, Error>` return
    /// (`clippy::result_large_err`).
    #[error("WebSocket error: {0:?}")]
    WebSocketError(#[source] Box<tokio_tungstenite::tungstenite::Error>),

    #[error("Unknown error: {0:?}")]
    UnknownError(#[source] anyhow::Error),
}

impl From<tokio_tungstenite::tungstenite::Error> for Error {
    fn from(e: tokio_tungstenite::tungstenite::Error) -> Self {
        Error::WebSocketError(Box::new(e))
    }
}

impl Error {
    /// Whether the site refused our credentials rather than failing some other
    /// way. 401 is a missing or unrecognised token; 403 is a token the server
    /// knows but will not accept for this. Both mean the same thing to a user,
    /// and both are worth telling them about specifically rather than showing
    /// a status code, because both have the same fix.
    pub fn is_auth_failure(&self) -> bool {
        matches!(
            self,
            Error::StatusError(StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN)
        )
    }
}

type Result<R> = std::result::Result<R, Error>;
