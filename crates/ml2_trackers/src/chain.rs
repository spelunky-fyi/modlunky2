//! Generic quest-chain finite state machine. Concrete chains
//! (Cosmic, Eggplant, Sunken) live in their own modules.
//!
//! Design notes:
//! - `Step<C>` is a fn-pointer taking a caller-defined `Context`.
//!   Concrete chains supply their own context type (whatever bundles
//!   the state + inventory + entity index they need); the trait
//!   requires no allocations per step.
//! - Callers express "advance to method X" as a bare function that
//!   receives the context and dispatches. The step tag is a fn
//!   pointer, giving equality and hashing for free (used for the
//!   "IN_PROGRESS returning the initial step" invariant check).

use std::fmt;

/// FSM status.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ChainStatus {
    /// The chain is waiting for the player to perform its first step.
    Unstarted,
    /// The chain is at some step beyond its first.
    InProgress,
    /// The chain failed and is stuck in that state.
    Failed,
}

impl ChainStatus {
    pub fn is_unstarted(&self) -> bool {
        matches!(self, ChainStatus::Unstarted)
    }
    pub fn is_in_progress(&self) -> bool {
        matches!(self, ChainStatus::InProgress)
    }
    pub fn is_failed(&self) -> bool {
        matches!(self, ChainStatus::Failed)
    }
}

/// One step's evaluator. Takes the caller-defined context and returns
/// the transition result. Fn pointer (not closure) so the FSM doesn't allocate
/// on every step and so callers can compare step identity for the
/// "no re-entering the initial step" invariant.
pub type Step<C> = fn(&C) -> ChainStepResult<C>;

/// The result of evaluating one step. `next_step` MUST be `Some` iff
/// `status == InProgress`; the constructors below enforce that
/// invariant so callers can't build a bad result.
#[derive(Clone, Copy)]
pub struct ChainStepResult<C> {
    pub status: ChainStatus,
    pub next_step: Option<Step<C>>,
}

impl<C> ChainStepResult<C> {
    pub fn unstarted() -> Self {
        Self {
            status: ChainStatus::Unstarted,
            next_step: None,
        }
    }

    pub fn in_progress(next: Step<C>) -> Self {
        Self {
            status: ChainStatus::InProgress,
            next_step: Some(next),
        }
    }

    pub fn failed() -> Self {
        Self {
            status: ChainStatus::Failed,
            next_step: None,
        }
    }
}

impl<C> fmt::Debug for ChainStepResult<C> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // Skip the fn pointer's raw address; log the status only.
        f.debug_struct("ChainStepResult")
            .field("status", &self.status)
            .field("has_next", &self.next_step.is_some())
            .finish()
    }
}

impl<C> PartialEq for ChainStepResult<C> {
    fn eq(&self, other: &Self) -> bool {
        // fn pointers implement PartialEq at the address level; two
        // steps compare equal iff they're the same function. Used
        // for the "changed between calls" check inside ChainStepper.
        self.status == other.status
            && match (self.next_step, other.next_step) {
                (Some(a), Some(b)) => (a as usize) == (b as usize),
                (None, None) => true,
                _ => false,
            }
    }
}

/// FSM runner. Constructed with an initial step; each call to
/// `evaluate` advances one transition and returns the new status.
///
/// The type parameter `C` is the caller-defined step context.
/// Concrete chains might use `C = ChainContext<'a>` where
/// `ChainContext` bundles a `&State`, `&HashSet<EntityType>`, etc.
pub struct ChainStepper<C> {
    name: &'static str,
    initial_step: Step<C>,
    last_result: ChainStepResult<C>,
}

impl<C> ChainStepper<C> {
    pub fn new(name: &'static str, initial_step: Step<C>) -> Self {
        Self {
            name,
            initial_step,
            last_result: ChainStepResult::unstarted(),
        }
    }

    pub fn name(&self) -> &'static str {
        self.name
    }

    /// Advance the FSM one transition.
    /// - Failed: stay failed, return Failed.
    /// - Unstarted: run the initial step.
    /// - InProgress: run whatever step the previous result named.
    ///
    /// Panics if a step returns `InProgress(initial_step)`, since
    /// re-entering the initial step from a non-initial state would
    /// erase progress.
    pub fn evaluate(&mut self, ctx: &C) -> ChainStatus {
        if self.last_result.status.is_failed() {
            return ChainStatus::Failed;
        }
        let step = if self.last_result.status.is_unstarted() {
            self.initial_step
        } else {
            // Guaranteed Some by the invariant on ChainStepResult.
            self.last_result
                .next_step
                .expect("in_progress result missing next_step")
        };
        let result = step(ctx);
        if result.status.is_in_progress()
            && let Some(next) = result.next_step
            && (next as usize) == (self.initial_step as usize)
        {
            panic!(
                "chain {}: step returned InProgress with the initial step",
                self.name
            );
        }
        self.last_result = result;
        self.last_result.status
    }

    pub fn last_status(&self) -> ChainStatus {
        self.last_result.status
    }

    /// Test seam: force the stepper's cached status without driving
    /// the FSM through its steps. RunState tests use this to
    /// short-circuit chain evaluation while testing the update
    /// methods that read `last_status()`. For `InProgress` this plants
    /// a dummy `next_step` pointing at the initial step; nothing
    /// consumes it because those tests never call `evaluate()` on
    /// the stepper again.
    #[cfg(test)]
    pub(crate) fn set_last_status_for_test(&mut self, status: ChainStatus) {
        self.last_result = match status {
            ChainStatus::Unstarted => ChainStepResult::unstarted(),
            ChainStatus::InProgress => ChainStepResult::in_progress(dummy_step_for_test),
            ChainStatus::Failed => ChainStepResult::failed(),
        };
    }
}

/// Placeholder `Step<C>` used only by `set_last_status_for_test` to
/// satisfy `ChainStepResult::in_progress`'s `next_step` requirement.
/// Never actually invoked because forced-status tests read
/// `last_status()` without re-driving the FSM.
#[cfg(test)]
fn dummy_step_for_test<C>(_: &C) -> ChainStepResult<C> {
    ChainStepResult::unstarted()
}
