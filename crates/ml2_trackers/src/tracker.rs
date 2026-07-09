//! The `TrackerTicker` trait + shared payload envelope.
//!
//! Every concrete tracker (Category, Pacifist, Timer, Gem,
//! Pacino Golf, CO) implements the same tiny trait: give it a
//! `TrackerContext` and it returns a `TrackerPayload`. Downstream
//! consumers (WebSocket handler, file writer, in-app window) all
//! subscribe to the same watch channel and choose how to render the
//! payload.
//!
//! Design mirrors HD-Toolbox's `TrackerTicker` + `Response` shape:
//! - Enum tagged with `type: "Category"` / `Empty` / `Failure` at the
//!   JSON level so a single WS client can handle any tracker output
//!   uniformly.
//! - Tick is sync because the process reads are sync (Windows'
//!   ReadProcessMemory is blocking). The runtime wrapper calls this
//!   from a `tokio::task::spawn_blocking` or a dedicated OS thread
//!   so it doesn't stall the axum runtime.
//! - Config is a Serialize + Deserialize + Default type owned by the
//!   ticker so config changes hot-reload without touching the tick
//!   loop.

use serde::{Deserialize, Serialize};

use crate::chain_impl::inputs::ChainInputs;
use ml2_mem::Spel2Process;

/// Input bundle for a single tick. Optional inputs because the game
/// may not be running, in which case trackers report `Empty`.
pub struct TrackerContext<'a> {
    /// Precomputed inputs when the game is attached; None means no
    /// process yet (game not running or attach failed).
    pub inputs: Option<&'a ChainInputs>,
    /// Raw process handle for the CO tracker, which needs to read a
    /// bank of theme sub-addresses at a fixed offset from the game's
    /// feedcode. Every other tracker consumes only `inputs` and
    /// leaves this None-or-not.
    pub process: Option<&'a Spel2Process>,
}

/// Serde-tagged payload envelope. Every WS message a client sees is
/// `{"type": "...", "data": {...}}` or `{"type": "Empty"}` for the
/// no-game case, so a single dispatcher in the browser-source JS
/// can route by tag.
#[derive(Debug, Clone, PartialEq, Serialize)]
#[serde(tag = "type", content = "data")]
pub enum TrackerPayload {
    Category(CategoryPayload),
    Pacifist(PacifistPayload),
    Timer(TimerPayload),
    Gem(GemPayload),
    PacinoGolf(PacinoGolfPayload),
    Co(CoPayload),
    /// Game hasn't been seen yet this tick task's lifetime. Renders as
    /// "Waiting for Spelunky 2" on the OBS side and clears the file
    /// output.
    Empty,
    /// The game was attached earlier but the tick task lost it (three
    /// consecutive read errors, drop the handle). Rendered distinctly
    /// from Empty so a streamer can tell "the game crashed" from
    /// "the game hasn't started yet".
    Detached,
    /// Anything that went wrong deeper (deserialize failure, torn
    /// read repeated, etc). Renders as a small error string for the
    /// tracker author, not the end user.
    Failure(String),
}

impl TrackerPayload {
    /// The plain string every downstream consumer displays: OBS Text
    /// source's file contents, tracker window label, etc. `Empty` /
    /// `Detached` resolve to an empty string so a stopped tracker
    /// blanks the file rather than leaving a stale label on-screen.
    pub fn text(&self) -> &str {
        match self {
            TrackerPayload::Category(p) => &p.text,
            TrackerPayload::Pacifist(p) => &p.text,
            TrackerPayload::Timer(p) => &p.text,
            TrackerPayload::Gem(p) => &p.text,
            TrackerPayload::PacinoGolf(p) => &p.text,
            TrackerPayload::Co(p) => &p.text,
            TrackerPayload::Empty | TrackerPayload::Detached => "",
            TrackerPayload::Failure(s) => s,
        }
    }
}

/// Category tracker's display payload. Just a string today; grows
/// with additional metadata (final-death flag for styling, current
/// terminus for icon selection) as the front-end evolves.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CategoryPayload {
    pub text: String,
    /// True after `RunState.final_death` fires. Front-end may style
    /// the label differently or freeze the string.
    pub final_death: bool,
}

/// A tracker that produces payloads on demand. Implementations own
/// whatever internal state they need to accumulate across ticks
/// (RunState for Category, per-level timers for Timer, kill counts
/// for Pacifist, etc).
pub trait TrackerTicker: Send + 'static {
    type Config: Serialize + for<'de> Deserialize<'de> + Default + Clone + Send + Sync + 'static;

    /// Display name; used for the WebSocket route (`/ws/{name}`),
    /// the file output (`trackers/{name}.txt`), and log lines.
    fn name(&self) -> &'static str;

    /// Advance the tracker one tick and return the current payload.
    /// Called at up to ~60 Hz; must be cheap when the game isn't
    /// attached (returns `Empty` immediately from the None branch).
    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload;

    /// When true, this tracker never spawns a file-mirror task and the
    /// UI hides the file-mirror knob. Set on trackers whose payload
    /// string changes every frame (currently just Timer) so the disk
    /// isn't rewritten 60x/second.
    fn never_writes_file(&self) -> bool {
        false
    }

    /// Called by the tick task every time the game process is (re)
    /// attached: first attach + every reattach after the game exits
    /// and comes back. Trackers that accumulate state across ticks
    /// (session timers, IL splits, per-run counters, cached process-
    /// specific LUTs) must clear it here so a fresh game process
    /// doesn't inherit the previous one's numbers. The tick task
    /// invokes it once between `Spel2Process::attach()` succeeding
    /// and the first subsequent `tick()`.
    fn on_attach(&mut self) {}
}

// ---------------------------------------------------------------------
// Category tracker
// ---------------------------------------------------------------------

use crate::runstate::{CategoryTrackerConfig, RunState};

/// Wraps `RunState` in the `TrackerTicker` shape. Owns its RunState
/// across ticks; downstream consumers (WS handlers, file writers) see
/// a fresh `CategoryPayload` whenever the display string changes.
pub struct CategoryTracker {
    run_state: RunState,
    /// Previous tick's `state.time_total`. The game's total-time
    /// counter monotonically climbs during a run and drops back to 0
    /// when a new run starts; a decrease here is the reset signal
    /// that a fresh `RunState` needs to swap in.
    prev_time_total: u32,
}

impl CategoryTracker {
    pub fn new() -> Self {
        Self {
            run_state: RunState::new(),
            prev_time_total: 0,
        }
    }
}

impl Default for CategoryTracker {
    fn default() -> Self {
        Self::new()
    }
}

impl TrackerTicker for CategoryTracker {
    type Config = CategoryTrackerConfig;

    fn name(&self) -> &'static str {
        "category"
    }

    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload {
        let Some(inputs) = ctx.inputs else {
            return TrackerPayload::Empty;
        };
        // RunState resolves new entity UIDs against the process,
        // so the process handle from ctx is required. If it's missing
        // (shouldn't happen in production; only in unit tests), skip
        // this tick's update entirely rather than partial.
        let Some(process) = ctx.process else {
            return TrackerPayload::Empty;
        };
        // Reset RunState when the game's total-time counter drops. It
        // ticks up monotonically during a run and resets to 0 when a
        // new run begins, so a decrease is the moment to wipe carried
        // state (`final_death`, discarded modifier labels, chain
        // stepper positions) that would otherwise stick from the
        // previous attempt. Without this, Death% persists across
        // restarts and modifier chains "instantly fail" on the new
        // run because their per-run history hasn't been cleared.
        let new_time_total = inputs.state.time_total;
        if new_time_total < self.prev_time_total {
            self.run_state = RunState::new();
        }
        self.prev_time_total = new_time_total;
        self.run_state.update(inputs, process);
        let screen = inputs.state.screen;
        TrackerPayload::Category(CategoryPayload {
            text: self.run_state.get_display(screen, config),
            final_death: self.run_state.is_final_death(),
        })
    }
}

/// Category-tracker config gets a serde derive so
/// `TrackerTicker::Config`'s bounds are satisfied and the tauri-side
/// store can persist it verbatim. Field names use kebab-case JSON via
/// `serde(rename_all)`.
///
/// NOTE: implemented in `runstate.rs` (that's where the type lives).
/// The impl there uses field renaming so an existing `modlunky2.json`
/// round-trips without losing the user's Category-tracker settings.
// ---------------------------------------------------------------------
// Pacifist tracker
// ---------------------------------------------------------------------
use crate::flags::RunRecapFlags;

/// Pacifist tracker's display payload. Kill count carries even when
/// the run is still Pacifist so a client that wants to show "0
/// kills / Pacifist" can, but the default renderer just shows the
/// `text` field.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct PacifistPayload {
    pub text: String,
    /// True once any kill has been registered, so the client can
    /// style the label differently (typically red).
    pub broken: bool,
    /// Total kills summed across every player's inventory.
    pub kills_total: u32,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case", default)]
pub struct PacifistTrackerConfig {
    /// When true, the "broken" label reads `MURDERED {n}!` with the
    /// running kill count. When false it just says `MURDERER!`.
    pub show_kill_count: bool,
}

/// Pacifist-tracker: watches the game's `RunRecapFlags::PACIFIST`
/// bit + the sum of `kills_total` across all four players. Renders
/// `Pacifist` while the flag is set, `MURDERED {n}!` (or
/// `MURDERER!`) after the first kill.
///
/// Truly stateless per-tick: the current run's kill count comes
/// straight from the inventories, not from an accumulator here. An
/// app restart mid-run therefore picks up where it left off.
pub struct PacifistTracker;

impl PacifistTracker {
    pub fn new() -> Self {
        Self
    }
}

impl Default for PacifistTracker {
    fn default() -> Self {
        Self::new()
    }
}

impl TrackerTicker for PacifistTracker {
    type Config = PacifistTrackerConfig;

    fn name(&self) -> &'static str {
        "pacifist"
    }

    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload {
        let Some(inputs) = ctx.inputs else {
            return TrackerPayload::Empty;
        };
        let is_pacifist = inputs
            .state
            .run_recap_flags
            .contains(RunRecapFlags::PACIFIST);
        let kills_total = inputs.all_players_kills_total;
        let (text, broken) = if is_pacifist {
            ("Pacifist".to_string(), false)
        } else if config.show_kill_count {
            (format!("MURDERED {kills_total}!"), true)
        } else {
            ("MURDERER!".to_string(), true)
        };
        TrackerPayload::Pacifist(PacifistPayload {
            text,
            broken,
            kills_total,
        })
    }
}

// ---------------------------------------------------------------------
// Timer tracker
// ---------------------------------------------------------------------

use std::time::Instant;

use crate::enums::Theme;

/// Snapshot of a completed level's timing. Kept per-run so the IL
/// list can rebuild whenever the runner resets.
#[derive(Debug, Clone, PartialEq)]
pub struct IlSplit {
    pub world: u8,
    pub level: u8,
    pub theme: Theme,
    /// Time on the level in game frames (60 Hz).
    pub time_frames: u32,
}

/// Timer tracker's display payload. Single `text` field with newline
/// separators; the OBS-side CSS renders `\n` as line breaks.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct TimerPayload {
    pub text: String,
}

/// Which timers appear in the label. Defaults: total/level/last-level
/// on; the rest off.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct TimerTrackerConfig {
    #[serde(default = "true_")]
    pub show_total: bool,
    #[serde(default = "true_")]
    pub show_level: bool,
    #[serde(default = "true_")]
    pub show_last_level: bool,
    #[serde(default)]
    pub show_tutorial: bool,
    #[serde(default)]
    pub show_session: bool,
    #[serde(default)]
    pub show_ils: bool,
}

fn true_() -> bool {
    true
}

impl Default for TimerTrackerConfig {
    fn default() -> Self {
        Self {
            show_total: true,
            show_level: true,
            show_last_level: true,
            show_tutorial: false,
            show_session: false,
            show_ils: false,
        }
    }
}

pub struct TimerTracker {
    /// Wall-clock instant the tracker booted at. Session timer counts
    /// wall-clock frames forward from here plus the initial startup
    /// value.
    session_start: Option<Instant>,
    /// Game's `time_startup` from the first observation. Captured
    /// once on first successful tick.
    initial_startup: Option<u32>,
    /// Per-level timings appended when the game's level_count grows;
    /// popped down when the runner resets (level_count shrinks).
    il_times: Vec<IlSplit>,
    /// `level_count` observed on the first successful tick, or the
    /// level_count of the "run reset" transition when level_count
    /// drops to zero. IL list is only meaningful when this is 0
    /// (fresh run started from base camp).
    first_level: Option<u8>,
}

impl TimerTracker {
    pub fn new() -> Self {
        Self {
            session_start: None,
            initial_startup: None,
            il_times: Vec::new(),
            first_level: None,
        }
    }

    fn format_frames(frames: u32) -> String {
        // frames / 60 = seconds; render HH:MM:SS.mmm without a
        // date-library dependency.
        let total_ms: u64 = (frames as u64 * 1000) / 60;
        let hours = total_ms / 3_600_000;
        let mins = (total_ms % 3_600_000) / 60_000;
        let secs = (total_ms % 60_000) / 1000;
        let millis = total_ms % 1000;
        format!("{hours:02}:{mins:02}:{secs:02}.{millis:03}")
    }
}

impl Default for TimerTracker {
    fn default() -> Self {
        Self::new()
    }
}

impl TrackerTicker for TimerTracker {
    type Config = TimerTrackerConfig;

    fn name(&self) -> &'static str {
        "timer"
    }

    /// Timer's payload string changes every frame (millisecond precision
    /// with a 60 Hz tick), so mirroring to disk would rewrite the file
    /// ~60 times a second for the whole session. The fix is to skip
    /// the file-mirror task entirely and hide the UI knob.
    fn never_writes_file(&self) -> bool {
        true
    }

    /// A new game process means `initial_startup` (captured once from
    /// the first tick) and `session_start` (wall-clock baseline) both
    /// belong to a dead process. Leaving them in place makes the
    /// session timer read the old game's uptime + the new game's
    /// wall-clock, which drifts hours off the truth. Rebuild from
    /// scratch on every attach; the next tick re-captures both.
    fn on_attach(&mut self) {
        *self = Self::new();
    }

    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload {
        let Some(inputs) = ctx.inputs else {
            return TrackerPayload::Empty;
        };
        let state = &inputs.state;

        // Capture startup + wall-clock start on first observation.
        let initial_startup = *self.initial_startup.get_or_insert(state.time_startup);
        let session_start = *self.session_start.get_or_insert_with(Instant::now);
        let session_frames =
            initial_startup as u64 + (session_start.elapsed().as_secs_f64() * 60.0) as u64;

        // IL bookkeeping. `first_level` locks in the level_count we
        // started at OR resets to 0 when the game shows level_count
        // 0 (a run start). Only when first_level == Some(0) do we
        // render the IL list.
        if self.first_level.is_none() || state.level_count == 0 {
            self.first_level = Some(state.level_count);
        }
        while self.il_times.len() > state.level_count as usize {
            self.il_times.pop();
        }
        if state.level_count as usize > self.il_times.len() {
            self.il_times.push(IlSplit {
                world: state.world,
                level: state.level,
                theme: state.theme,
                time_frames: state.time_level,
            });
        }

        let mut lines: Vec<String> = Vec::with_capacity(6);
        if config.show_total {
            lines.push(format!("Total: {}", Self::format_frames(state.time_total)));
        }
        if config.show_level {
            lines.push(format!("Level: {}", Self::format_frames(state.time_level)));
        }
        if config.show_last_level {
            lines.push(format!(
                "Last: {}",
                Self::format_frames(state.time_last_level)
            ));
        }
        if config.show_tutorial {
            lines.push(format!(
                "Tutorial: {}",
                Self::format_frames(state.time_tutorial)
            ));
        }
        if config.show_session {
            lines.push(format!(
                "Session: {}",
                Self::format_frames(session_frames.min(u32::MAX as u64) as u32)
            ));
        }
        if config.show_ils {
            if self.first_level == Some(0) {
                for il in &self.il_times {
                    lines.push(format!(
                        "{}-{}: {}",
                        il.world,
                        il.level,
                        Self::format_frames(il.time_frames)
                    ));
                }
            } else {
                lines.push("Reset run to track ILs".to_string());
            }
        }

        TrackerPayload::Timer(TimerPayload {
            text: lines.join("\n"),
        })
    }
}

// ---------------------------------------------------------------------
// Gem tracker
// ---------------------------------------------------------------------

use crate::entity::{DIAMOND, EntityType, GEMS};
use crate::enums::WinState;

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct GemPayload {
    pub text: String,
}

/// Which counts appear in the label. Defaults: total gem count on,
/// everything else off.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct GemTrackerConfig {
    #[serde(default = "true_")]
    pub show_total_gem_count: bool,
    #[serde(default)]
    pub show_colored_gem_count: bool,
    #[serde(default)]
    pub show_diamond_count: bool,
    #[serde(default)]
    pub show_yem_count: bool,
    #[serde(default)]
    pub show_diamond_percentage: bool,
}

impl Default for GemTrackerConfig {
    fn default() -> Self {
        Self {
            show_total_gem_count: true,
            show_colored_gem_count: false,
            show_diamond_count: false,
            show_yem_count: false,
            show_diamond_percentage: false,
        }
    }
}

pub struct GemTracker {
    /// Gems collected on previously-completed levels this run. The
    /// current level's count comes off ChainInputs each tick.
    gems_total: u32,
    diamonds_total: u32,
    yems_total: u32,
    /// Current level's rolling counts, cached so the level-change
    /// handler knows what to add to the totals before the game clears
    /// the underlying `collected_money` slots.
    gems_level: u32,
    diamonds_level: u32,
    yems_level: u32,
    world: u8,
    level: u8,
}

impl GemTracker {
    pub fn new() -> Self {
        Self {
            gems_total: 0,
            diamonds_total: 0,
            yems_total: 0,
            gems_level: 0,
            diamonds_level: 0,
            yems_level: 0,
            world: 0,
            level: 0,
        }
    }
}

impl Default for GemTracker {
    fn default() -> Self {
        Self::new()
    }
}

/// Levels where the ghost doesn't spawn, so colored gems collected
/// there aren't "yems".
fn level_has_ghost(theme: Theme) -> bool {
    !matches!(
        theme,
        Theme::BaseCamp
            | Theme::Olmec
            | Theme::Abzu
            | Theme::Duat
            | Theme::Tiamat
            | Theme::EggplantWorld
            | Theme::Hundun
            | Theme::CosmicOcean
    )
}

impl TrackerTicker for GemTracker {
    type Config = GemTrackerConfig;

    fn name(&self) -> &'static str {
        "gem"
    }

    /// Wipe carried counts + last-known (world, level) so the first
    /// tick against a fresh game process doesn't fold stale
    /// `gems_level` into `gems_total` on a spurious level-change
    /// detection.
    fn on_attach(&mut self) {
        *self = Self::new();
    }

    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload {
        let Some(inputs) = ctx.inputs else {
            return TrackerPayload::Empty;
        };
        let state = &inputs.state;

        // On level change, fold the level's rolling counts into the
        // run totals. Skip the base-camp transition: Camp doesn't have
        // gems and the transition would prematurely zero the level
        // counts before the next area's first tick.
        if (state.world != self.world || state.level != self.level)
            && state.theme != Theme::BaseCamp
        {
            self.world = state.world;
            self.level = state.level;
            self.gems_total += self.gems_level;
            self.diamonds_total += self.diamonds_level;
            self.yems_total += self.yems_level;
            self.gems_level = 0;
            self.diamonds_level = 0;
            self.yems_level = 0;
        }

        // Restart detection: back at the starting level with no win
        // yet. Clears the totals so a fresh run starts clean.
        if state.world == state.world_start
            && state.level == state.level_start
            && matches!(state.win_state, WinState::NoWin)
        {
            self.gems_total = 0;
            self.diamonds_total = 0;
            self.yems_total = 0;
        }

        // Re-count the current level from `collected_money` slots.
        let has_ghost = level_has_ghost(state.theme);
        let mut gems = 0u32;
        let mut diamonds = 0u32;
        let mut yems = 0u32;
        for entity_id in inputs.all_players_collected_money.iter().copied() {
            let ty = EntityType(entity_id);
            if GEMS.contains(&ty) {
                gems += 1;
                if ty == DIAMOND {
                    diamonds += 1;
                } else if has_ghost {
                    yems += 1;
                }
            }
        }
        self.gems_level = gems;
        self.diamonds_level = diamonds;
        self.yems_level = yems;

        let gems = self.gems_total + self.gems_level;
        let diamonds = self.diamonds_total + self.diamonds_level;
        let yems = self.yems_total + self.yems_level;

        let mut lines: Vec<String> = Vec::with_capacity(5);
        if config.show_total_gem_count {
            lines.push(format!("{:>13}: {:<4}", "Total gems", gems));
        }
        if config.show_colored_gem_count {
            lines.push(format!(
                "{:>13}: {:<4}",
                "Colorful gems",
                gems.saturating_sub(diamonds)
            ));
        }
        if config.show_diamond_count {
            lines.push(format!("{:>13}: {:<4}", "Diamonds", diamonds));
        }
        if config.show_yem_count {
            lines.push(format!("{:>13}: {:<4}", "Yems", yems));
        }
        if config.show_diamond_percentage {
            let denom = yems + diamonds;
            let rate = if denom > 0 {
                (diamonds as f64 / denom as f64 * 100.0).round() as u32
            } else {
                0
            };
            lines.push(format!("{:>13}: {:<4}", "Diamond rate", format!("{rate}%")));
        }

        TrackerPayload::Gem(GemPayload {
            text: lines.join("\n"),
        })
    }
}

// ---------------------------------------------------------------------
// Pacino Golf tracker
// ---------------------------------------------------------------------

/// Golf tracker owns its own RunState so its low% check is
/// independent of any Category tracker instance the app might also
/// be running.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct PacinoGolfPayload {
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct PacinoGolfTrackerConfig {
    #[serde(default = "true_")]
    pub show_total_strokes: bool,
    #[serde(default)]
    pub show_resource_strokes: bool,
    #[serde(default)]
    pub show_treasure_strokes: bool,
    #[serde(default)]
    pub show_pacifist_strokes: bool,
}

impl Default for PacinoGolfTrackerConfig {
    fn default() -> Self {
        Self {
            show_total_strokes: true,
            show_resource_strokes: false,
            show_treasure_strokes: false,
            show_pacifist_strokes: false,
        }
    }
}

pub struct PacinoGolfTracker {
    run_state: RunState,
    world: u8,
    level: u8,
    /// Cached at the top of every tick so a torn read on the player
    /// snapshot falls back to the last known values.
    bombs: u8,
    ropes: u8,
    /// Treasure accumulated on completed levels + on the current
    /// level. Split so a level-transition folds `_level` into `_total`.
    treasure_strokes: u32,
    treasure_strokes_level: u32,
    resource_strokes: u32,
    pacifist_strokes: u32,
    /// Watchdog for run reset. `time_total` monotonically increases
    /// during a run; a drop means the game just started a fresh one.
    prev_time_total: u32,
}

impl PacinoGolfTracker {
    const STARTING_RESOURCES: i32 = 12;

    pub fn new() -> Self {
        Self {
            run_state: RunState::new(),
            world: 0,
            level: 0,
            bombs: 4,
            ropes: 4,
            treasure_strokes: 0,
            treasure_strokes_level: 0,
            resource_strokes: 0,
            pacifist_strokes: 0,
            prev_time_total: 0,
        }
    }

    fn reset_run(&mut self) {
        self.run_state = RunState::new();
        self.world = 0;
        self.level = 0;
        self.bombs = 4;
        self.ropes = 4;
        self.treasure_strokes = 0;
        self.treasure_strokes_level = 0;
        self.resource_strokes = 0;
        self.pacifist_strokes = 0;
        self.prev_time_total = 0;
    }
}

impl Default for PacinoGolfTracker {
    fn default() -> Self {
        Self::new()
    }
}

impl TrackerTicker for PacinoGolfTracker {
    type Config = PacinoGolfTrackerConfig;

    fn name(&self) -> &'static str {
        "pacino-golf"
    }

    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload {
        let Some(inputs) = ctx.inputs else {
            return TrackerPayload::Empty;
        };
        let state = &inputs.state;

        // Fresh run detection.
        if state.time_total < self.prev_time_total {
            self.reset_run();
        }
        self.prev_time_total = state.time_total;

        // RunState resolves new entity UIDs against the process,
        // so the process handle from ctx is required. If it's missing
        // (shouldn't happen in production; only in unit tests), skip
        // this tick's update entirely rather than partial.
        let Some(process) = ctx.process else {
            return TrackerPayload::Empty;
        };
        self.run_state.update(inputs, process);
        let is_low = self.run_state.is_low_percent();

        // Level change: bank the current level's treasure count.
        if (state.world != self.world || state.level != self.level)
            && state.theme != Theme::BaseCamp
        {
            self.world = state.world;
            self.level = state.level;
            self.treasure_strokes += self.treasure_strokes_level;
            self.treasure_strokes_level = 0;
        }

        // Restart detection.
        if state.world == state.world_start
            && state.level == state.level_start
            && matches!(state.win_state, WinState::NoWin)
        {
            self.treasure_strokes = 0;
        }

        // Resources used (player 0 only, singleplayer-oriented).
        let mut resources_used = 0i32;
        if !matches!(state.theme, Theme::BeforeFirstRun | Theme::BaseCamp) {
            if let Some(player) = &inputs.player0 {
                self.bombs = player.inventory.bombs;
                self.ropes = player.inventory.ropes;
                let health = player.health.max(0) as i32;
                resources_used =
                    Self::STARTING_RESOURCES - self.bombs as i32 - self.ropes as i32 - health;
            } else {
                // Player pointer missing (mid-transition torn read);
                // treat health as 0, keep last known bombs/ropes.
                resources_used = Self::STARTING_RESOURCES - self.bombs as i32 - self.ropes as i32;
            }
        }

        let treasure_collected = inputs.all_players_collected_money.len() as u32;
        self.treasure_strokes_level = treasure_collected;
        self.resource_strokes = resources_used.max(0) as u32;
        self.pacifist_strokes = inputs.all_players_kills_total;

        let total_strokes = self.resource_strokes
            + (self.treasure_strokes + self.treasure_strokes_level)
            + self.pacifist_strokes;

        let mut lines: Vec<String> = Vec::with_capacity(4);
        if config.show_total_strokes {
            if is_low {
                lines.push(format!("Strokes: {total_strokes}"));
            } else {
                lines.push("Strokes: \u{221E}".to_string());
            }
        }
        if config.show_resource_strokes {
            lines.push(format!("Resources used: {}", self.resource_strokes));
        }
        if config.show_treasure_strokes {
            lines.push(format!(
                "Treasure: {}",
                self.treasure_strokes + self.treasure_strokes_level
            ));
        }
        if config.show_pacifist_strokes {
            lines.push(format!("Kills: {}", self.pacifist_strokes));
        }

        TrackerPayload::PacinoGolf(PacinoGolfPayload {
            text: lines.join("\n"),
        })
    }
}

// ---------------------------------------------------------------------
// CO tracker
// ---------------------------------------------------------------------

use ml2_mem::read_u64;
use std::collections::HashMap;

/// Distance from the feedcode marker to the 8-entry level-gen table
/// the CO tracker samples.
const CO_OFFSET_TO_LEVEL_GEN: u64 = 0xD7631;
/// Stride between the 8 theme addresses in the level-gen table.
const CO_THEME_STRIDE: u64 = 0x8;

/// The eight themes CO's sub-theme address can resolve to. Order +
/// slot indices match the exe's level-gen table.
const CO_THEMES: &[(u64, Theme)] = &[
    (2, Theme::Dwelling),
    (3, Theme::Jungle),
    (4, Theme::Volcana),
    (6, Theme::TidePool),
    (7, Theme::Temple),
    (8, Theme::IceCaves),
    (9, Theme::NeoBabylon),
    (10, Theme::SunkenCity),
];

/// Theme name style the label uses. Kebab-case on the wire so it
/// round-trips with the legacy string enum values.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ThemeNameStyle {
    #[default]
    #[serde(rename = "Full theme names")]
    Full,
    #[serde(rename = "Short theme names")]
    Short,
    #[serde(rename = "Two-letter theme names")]
    TwoLetter,
    #[serde(rename = "No theme names")]
    None_,
}

fn theme_label(style: ThemeNameStyle, theme: Theme) -> Option<&'static str> {
    match style {
        ThemeNameStyle::None_ => None,
        ThemeNameStyle::Full => Some(match theme {
            Theme::Dwelling => "Dwelling",
            Theme::Jungle => "Jungle",
            Theme::Volcana => "Volcana",
            Theme::TidePool => "Tide Pool",
            Theme::Temple => "Temple",
            Theme::IceCaves => "Ice Caves",
            Theme::NeoBabylon => "Neo Babylon",
            Theme::SunkenCity => "Sunken City",
            _ => "",
        }),
        ThemeNameStyle::Short => Some(match theme {
            Theme::Dwelling => "Dwelling",
            Theme::Jungle => "Jungle",
            Theme::Volcana => "Volcana",
            Theme::TidePool => "TidePool",
            Theme::Temple => "Temple",
            Theme::IceCaves => "IceCaves",
            Theme::NeoBabylon => "NeoBab",
            Theme::SunkenCity => "Sunken",
            _ => "",
        }),
        ThemeNameStyle::TwoLetter => Some(match theme {
            Theme::Dwelling => "DW",
            Theme::Jungle => "JU",
            Theme::Volcana => "VO",
            Theme::TidePool => "TP",
            Theme::Temple => "TE",
            Theme::IceCaves => "IC",
            Theme::NeoBabylon => "NB",
            Theme::SunkenCity => "SC",
            _ => "",
        }),
    }
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct CoPayload {
    pub text: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub struct CoTrackerConfig {
    #[serde(default)]
    pub theme_name_style: ThemeNameStyle,
    #[serde(default = "true_")]
    pub show_run_stats: bool,
    #[serde(default = "true_")]
    pub show_session_stats: bool,
    #[serde(default = "true_")]
    pub show_header: bool,
}

impl Default for CoTrackerConfig {
    fn default() -> Self {
        Self {
            theme_name_style: ThemeNameStyle::default(),
            show_run_stats: true,
            show_session_stats: true,
            show_header: true,
        }
    }
}

pub struct CoTracker {
    world: u8,
    level: u8,
    /// Map from a level-gen sub-theme address to the Theme it names.
    /// Populated the first time the game's feedcode is readable; the
    /// LUT is stable across levels + resets, so build it once.
    address_to_theme: Option<HashMap<u64, Theme>>,
    session_stats: HashMap<Theme, u32>,
    run_stats: HashMap<Theme, u32>,
}

impl CoTracker {
    pub fn new() -> Self {
        Self {
            world: 0,
            level: 0,
            address_to_theme: None,
            session_stats: HashMap::new(),
            run_stats: HashMap::new(),
        }
    }

    fn build_address_lut(process: &Spel2Process) -> Option<HashMap<u64, Theme>> {
        let feedcode = process.get_feedcode().ok()?;
        let base = feedcode + CO_OFFSET_TO_LEVEL_GEN;
        let mut map = HashMap::with_capacity(CO_THEMES.len());
        for (slot, theme) in CO_THEMES.iter().copied() {
            let addr = read_u64(process, base + slot * CO_THEME_STRIDE).ok()?;
            map.insert(addr, theme);
        }
        Some(map)
    }

    fn add_theme(&mut self, theme: Theme) {
        *self.session_stats.entry(theme).or_insert(0) += 1;
        *self.run_stats.entry(theme).or_insert(0) += 1;
    }

    fn stats_str(counts: &HashMap<Theme, u32>, theme: Theme) -> String {
        let count = counts.get(&theme).copied().unwrap_or(0);
        let total: u32 = counts.values().sum();
        let pct = if total > 0 {
            (count as f64 / total as f64 * 100.0).round() as u32
        } else {
            0
        };
        let pct_str = format!("({pct}%)");
        format!("{count:>2} {pct_str:>6}")
    }

    fn display(&self, config: &CoTrackerConfig) -> String {
        // Column width for the theme-name gutter. Zero when name
        // style is None (no gutter drawn at all).
        let max_name_width: usize = if matches!(config.theme_name_style, ThemeNameStyle::None_) {
            0
        } else {
            CO_THEMES
                .iter()
                .map(|(_, t)| theme_label(config.theme_name_style, *t).unwrap_or("").len())
                .max()
                .unwrap_or(0)
        };

        let mut out = String::new();

        if config.show_header {
            let mut header: Vec<String> = Vec::new();
            if !matches!(config.theme_name_style, ThemeNameStyle::None_) {
                header.push(" ".repeat(max_name_width + 1));
            }
            if config.show_run_stats {
                header.push(format!("{:^9}", "Run"));
            }
            if config.show_session_stats {
                header.push(format!("{:^9}", "Session"));
            }
            if !header.is_empty() {
                out.push_str(&header.join(" "));
                out.push('\n');
            }
        }

        let mut lines: Vec<String> = Vec::with_capacity(CO_THEMES.len());
        for (_, theme) in CO_THEMES.iter().copied() {
            let mut parts: Vec<String> = Vec::new();
            if let Some(name) = theme_label(config.theme_name_style, theme) {
                parts.push(format!("{name:>width$}:", width = max_name_width));
            }
            if config.show_run_stats {
                parts.push(Self::stats_str(&self.run_stats, theme));
            }
            if config.show_session_stats {
                parts.push(Self::stats_str(&self.session_stats, theme));
            }
            lines.push(parts.join(" "));
        }
        out.push_str(&lines.join("\n"));
        out
    }
}

impl Default for CoTracker {
    fn default() -> Self {
        Self::new()
    }
}

impl TrackerTicker for CoTracker {
    type Config = CoTrackerConfig;

    fn name(&self) -> &'static str {
        "co"
    }

    /// address_to_theme is a LUT of process-space pointers pulled from
    /// the previous game's feedcode. Those addresses are meaningless
    /// against a fresh process; reading through them would classify
    /// every theme as garbage. Rebuild everything (LUT, session/run
    /// stats, and world/level) on attach.
    fn on_attach(&mut self) {
        *self = Self::new();
    }

    fn tick(&mut self, ctx: &TrackerContext<'_>, config: &Self::Config) -> TrackerPayload {
        let Some(inputs) = ctx.inputs else {
            return TrackerPayload::Empty;
        };

        // Lazy: LUT wants process access, which is only available
        // when attached (via TrackerContext.process).
        if self.address_to_theme.is_none()
            && let Some(process) = ctx.process
            && let Some(lut) = Self::build_address_lut(process)
        {
            self.address_to_theme = Some(lut);
        }

        let state = &inputs.state;
        let world = state.world;
        let level = state.level;

        if world != self.world || level != self.level {
            self.world = world;
            self.level = level;

            // Only sample the sub-theme on level < 99; the CO end-run
            // screen sits above that cap and shouldn't count.
            if matches!(state.theme, Theme::CosmicOcean)
                && level < 99
                && let (Some(lut), Some(addr)) =
                    (&self.address_to_theme, inputs.theme_info_sub_theme_address)
                && let Some(theme) = lut.get(&addr).copied()
            {
                self.add_theme(theme);
            }

            // Fresh run detection: land back at the run's starting
            // (world, level) OR bounce through base camp.
            let restarted = world == state.world_start && level == state.level_start;
            if restarted || matches!(state.theme, Theme::BaseCamp) {
                self.run_stats.clear();
            }
        }

        TrackerPayload::Co(CoPayload {
            text: self.display(config),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_context_returns_empty_payload() {
        let mut tracker = CategoryTracker::new();
        let ctx = TrackerContext {
            inputs: None,
            process: None,
        };
        let cfg = CategoryTrackerConfig::default();
        assert_eq!(tracker.tick(&ctx, &cfg), TrackerPayload::Empty);
    }

    #[test]
    fn empty_payload_json_shape() {
        let payload = TrackerPayload::Empty;
        let s = serde_json::to_string(&payload).unwrap_or_default();
        // Serde tag serializes as `{"type":"Empty"}`, no `data`
        // because the variant has no fields.
        assert!(s.contains("\"type\":\"Empty\""));
    }

    #[test]
    fn category_payload_json_shape() {
        let payload = TrackerPayload::Category(CategoryPayload {
            text: "No%".into(),
            final_death: false,
        });
        let s = serde_json::to_string(&payload).unwrap_or_default();
        assert!(s.contains("\"type\":\"Category\""));
        assert!(s.contains("\"text\":\"No%\""));
        assert!(s.contains("\"final_death\":false"));
    }
}
