use std::error::Error;
use std::time::Duration;

use backon::{BackoffBuilder, ExponentialBackoff, ExponentialBuilder};
use tokio::time::Sleep;

/// Match the previously-used `backoff` crate defaults so retry cadence
/// stays the same across the migration: 500ms initial, 1.5x factor, 60s
/// cap, unlimited retries, jitter on.
fn build_backoff() -> ExponentialBackoff {
    ExponentialBuilder::default()
        .with_min_delay(Duration::from_millis(500))
        .with_factor(1.5)
        .with_max_delay(Duration::from_secs(60))
        .with_jitter()
        .without_max_times()
        .build()
}

pub enum BackoffKind {
    Restart,
    Transient,
    Permanent,
}

pub trait AsBackoffKind {
    fn as_backoff_kind(&self) -> BackoffKind;
}

pub struct RetryPolicy {
    backoff: ExponentialBackoff,
}

impl std::fmt::Debug for RetryPolicy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("RetryPolicy").finish_non_exhaustive()
    }
}

impl RetryPolicy {
    pub fn new() -> Self {
        RetryPolicy {
            backoff: build_backoff(),
        }
    }

    pub fn wait_to_retry<E: Error + AsBackoffKind>(
        &mut self,
        result: Result<(), E>,
    ) -> Result<Sleep, E> {
        match result.as_ref().map_err(|e| e.as_backoff_kind()) {
            Ok(()) | Err(BackoffKind::Restart) => {
                self.backoff = build_backoff();
                Ok(tokio::time::sleep(Duration::ZERO))
            }
            Err(BackoffKind::Transient) => self
                .backoff
                .next()
                .map(tokio::time::sleep)
                .ok_or_else(|| result.unwrap_err()),
            Err(BackoffKind::Permanent) => Err(result.unwrap_err()),
        }
    }
}

impl Default for RetryPolicy {
    fn default() -> Self {
        Self::new()
    }
}
