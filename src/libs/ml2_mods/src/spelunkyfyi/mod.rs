use ::http::{header::InvalidHeaderValue, StatusCode};

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
    #[error("WebSocket error: {0:?}")]
    WebSocketError(#[from] tokio_tungstenite::tungstenite::Error),

    #[error("Unknown error: {0:?}")]
    UnknownError(#[source] anyhow::Error),
}

type Result<R> = std::result::Result<R, Error>;
