use std::error::Error;
use std::time::Duration;

use backoff::backoff::Backoff;
use tokio::time::Sleep;

/// A clock backed by tokio::time. Notably, it honors Tokio's test utility functions
#[derive(Debug, Default)]
pub struct TokioClock;

impl backoff::Clock for TokioClock {
    fn now(&self) -> instant::Instant {
        tokio::time::Instant::now().into_std()
    }
}

pub type ExponentialBackoffBuilder = backoff::exponential::ExponentialBackoffBuilder<TokioClock>;
pub type ExponentialBackoff = backoff::exponential::ExponentialBackoff<TokioClock>;

pub enum BackoffKind {
    Restart,
    Transient,
    Permanent,
}

pub trait AsBackoffKind {
    fn as_backoff_kind(&self) -> BackoffKind;
}

#[derive(Debug)]
pub struct RetryPolicy {
    backoff: ExponentialBackoff,
}

impl RetryPolicy {
    pub fn new(builder: ExponentialBackoff) -> Self {
        RetryPolicy { backoff: builder }
    }

    pub fn wait_to_retry<E: Error + AsBackoffKind>(
        &mut self,
        result: Result<(), E>,
    ) -> Result<Sleep, E> {
        match result.as_ref().map_err(|e| e.as_backoff_kind()) {
            Ok(()) | Err(BackoffKind::Restart) => {
                self.backoff.reset();
                Ok(tokio::time::sleep(Duration::ZERO))
            }
            Err(BackoffKind::Transient) => self
                .backoff
                .next_backoff()
                .map(tokio::time::sleep)
                .ok_or_else(|| result.unwrap_err()),
            Err(BackoffKind::Permanent) => return Err(result.unwrap_err()),
        }
    }
}
