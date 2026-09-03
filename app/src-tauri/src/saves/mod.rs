//! The Saves tab: reading the live save, archiving it, and restoring.
//!
//! The game keeps one save, `savegame.sav`, in the root of its install
//! directory. Everything here works on that file. Copies of it are filed
//! into two libraries outside the game directory; see [`store`].
//!
//! # Restoring safely
//!
//! Restoring is the one destructive thing in here, and the save it
//! overwrites may well be further along than the one going in. So a
//! restore is a two-step conversation: [`preview_save_restore`] reports
//! which lifetime counters would go backwards, and [`restore_stored_save`]
//! archives the current save before replacing it. The comparison is real
//! rather than a timestamp check, because a save archived later is not
//! necessarily the one with more progress in it.
//!
//! # Threading
//!
//! Tauri runs a plain `#[tauri::command]` on the main thread, so anything
//! slow in one freezes the window. The commands that walk the whole
//! archive, or that write a save, are declared `#[tauri::command(async)]`
//! to move them onto the async runtime. The archive grows on its own, so
//! "slow" here is not hypothetical: listing parses every save in it.
//!
//! # Writing
//!
//! Every write goes to a temporary file in the destination directory and
//! is then renamed over the target. A crash mid-write leaves the old save
//! intact, which matters more here than anywhere else in the app: the
//! failure this feature exists to protect against is exactly a save that
//! got half-written.

pub mod editor;
pub mod retention;
pub mod snapshotter;
pub mod stickers;
pub mod store;

use std::path::{Path, PathBuf};

use ml2_save::{Constellation, ProgressComparison, SaveFile, SaveStats, SaveSummary};
use serde::{Deserialize, Serialize};
use tauri::AppHandle;

use retention::{RetentionPreview, RetentionSettings};
use store::{Library, SaveKind, StoredSave};

/// The game's save, in the root of the install directory.
pub const SAVE_FILENAME: &str = "savegame.sav";

/// Default gap between automatic snapshots.
const DEFAULT_INTERVAL_HOURS: u32 = 24;
/// Floor on the configured interval. Anything faster is not a snapshotter,
/// it is a disk-filling loop.
const MIN_INTERVAL_HOURS: u32 = 1;

/// Where the live save is, from the configured install directory.
pub fn save_path() -> Option<PathBuf> {
    crate::config::load()
        .install_dir
        .map(|d| d.join(SAVE_FILENAME))
}

/// How the automatic snapshotter is configured.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SnapshotSettings {
    /// Whether automatic snapshots are taken at all. Off by default: this
    /// writes files on the user's disk on a schedule, so it is opt-in.
    pub enabled: bool,
    /// Hours between automatic snapshots.
    pub interval_hours: u32,
    /// Which snapshots stay restorable. Defaults to keeping everything.
    ///
    /// Deserialized leniently: a value this build cannot read falls back
    /// to the default rather than failing the whole struct. Without that,
    /// one unreadable field would take `enabled` down with it and quietly
    /// stop snapshotting altogether, which is the worst possible way for
    /// a config change to go wrong.
    #[serde(default, deserialize_with = "lenient_retention")]
    pub retention: RetentionSettings,
}

/// Reads retention settings, falling back to the default on anything
/// unreadable instead of failing the parse.
fn lenient_retention<'de, D>(deserializer: D) -> Result<RetentionSettings, D::Error>
where
    D: serde::Deserializer<'de>,
{
    use serde::Deserialize;
    let value = serde_json::Value::deserialize(deserializer)?;
    Ok(serde_json::from_value(value).unwrap_or_default())
}

impl Default for SnapshotSettings {
    fn default() -> Self {
        Self {
            enabled: false,
            interval_hours: DEFAULT_INTERVAL_HOURS,
            retention: RetentionSettings::default(),
        }
    }
}

impl SnapshotSettings {
    /// Clamps values that would make the snapshotter misbehave.
    ///
    /// The retention tiers need no clamping: zero is a meaningful "switch
    /// this tier off", and `plan_pruning` guarantees the newest snapshot
    /// survives whatever the tiers add up to.
    fn sanitized(mut self) -> Self {
        self.interval_hours = self.interval_hours.max(MIN_INTERVAL_HOURS);
        self
    }
}

/// Reads the snapshotter settings from config.
pub fn settings() -> SnapshotSettings {
    crate::config::get_saves_settings().sanitized()
}

/// The live save, as the Saves tab sees it.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveStatus {
    /// Absolute path, or `None` when no install directory is configured.
    pub path: Option<String>,
    /// Whether a file is actually there.
    pub exists: bool,
    /// Last modified time, epoch milliseconds.
    pub modified_at_ms: Option<u64>,
    /// Size in bytes.
    pub file_size: Option<u64>,
    /// Stats, absent if the save could not be read.
    pub summary: Option<SaveSummary>,
    /// Why the save could not be read, when `summary` is absent. A
    /// corrupt save is the case this whole feature exists for, so the
    /// reason is surfaced rather than swallowed.
    pub error: Option<String>,
}

/// What restoring an archived save would do.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RestorePreview {
    /// The archived save that would be restored.
    pub stored: StoredSave,
    /// Stats that would move, in each direction.
    pub comparison: ProgressComparison,
    /// Whether any lifetime counter would go backwards.
    pub loses_progress: bool,
    /// Whether the current save and the snapshot look identical.
    pub identical: bool,
    /// Whether there is a readable save to compare against at all. When
    /// false the comparison is empty and the restore is unconditionally
    /// safe, because there is nothing to lose.
    pub has_current_save: bool,
}

fn err(context: &str, e: impl std::fmt::Display) -> String {
    format!("{context}: {e}")
}

/// Reads the live save's status.
#[tauri::command]
pub fn get_save_status() -> SaveStatus {
    let Some(path) = save_path() else {
        return SaveStatus {
            path: None,
            exists: false,
            modified_at_ms: None,
            file_size: None,
            summary: None,
            error: Some("No Spelunky 2 install directory is configured.".into()),
        };
    };

    let metadata = std::fs::metadata(&path).ok();
    let exists = metadata.is_some();
    let modified_at_ms = metadata.as_ref().and_then(|m| {
        m.modified()
            .ok()?
            .duration_since(std::time::UNIX_EPOCH)
            .ok()
            .map(|d| d.as_millis() as u64)
    });
    let file_size = metadata.as_ref().map(|m| m.len());

    let (summary, error) = if exists {
        match SaveFile::read(&path) {
            Ok(save) => (Some(SaveSummary::from_save(&save)), None),
            Err(e) => (None, Some(e.to_string())),
        }
    } else {
        (None, None)
    };

    SaveStatus {
        path: Some(path.display().to_string()),
        exists,
        modified_at_ms,
        file_size,
        summary,
        error,
    }
}

/// Saves the user made and named, newest first.
#[tauri::command(async)]
pub fn list_managed_saves() -> Result<Vec<StoredSave>, String> {
    store::list(Library::Managed).map_err(|e| err("Could not list saves", e))
}

/// Automatic snapshots, newest first.
#[tauri::command(async)]
pub fn list_save_snapshots() -> Result<Vec<StoredSave>, String> {
    store::list(Library::Snapshots).map_err(|e| err("Could not list snapshots", e))
}

/// A save file the user has pointed at, before it is copied in.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportPreview {
    pub path: String,
    /// The file's own name, for a default description.
    pub file_name: String,
    pub file_size: u64,
    /// When the file was last written, epoch milliseconds.
    pub modified_at_ms: Option<u64>,
    /// What is in it. Absent when it could not be read at all, in which
    /// case `error` says why.
    pub summary: Option<SaveSummary>,
    /// Why this file cannot be imported, if it cannot. A batch keeps
    /// going past one bad file rather than failing all of them.
    pub error: Option<String>,
    /// False for a file whose checksum does not verify. Still importable:
    /// a copy of a damaged save is exactly what an archive is for.
    pub checksum_valid: bool,
    /// The archived record already holding these exact bytes, if any.
    pub duplicate: Option<DuplicateRecord>,
}

/// Enough of an existing record to say what the duplicate is.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DuplicateRecord {
    pub id: String,
    pub description: String,
    pub taken_at_ms: u64,
    pub kind: SaveKind,
}

/// One file's outcome from an import.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportFailure {
    pub path: String,
    pub error: String,
}

/// What a batch import did.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportOutcome {
    pub imported: Vec<StoredSave>,
    /// Files that could not be copied. One bad file does not stop the
    /// rest, so both halves come back.
    pub failed: Vec<ImportFailure>,
}

/// One file to copy in, with the name it should be filed under.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ImportItem {
    pub path: String,
    pub description: String,
}

/// Reads the save files the user picked, without copying anything.
///
/// Reports what is in each and whether the archive already holds those
/// exact bytes, so an import can be confirmed rather than guessed at. A
/// file that cannot be read comes back with an `error` instead of a
/// summary rather than failing the whole batch: picking twenty files and
/// being told only that one of them is bad is not a useful answer.
#[tauri::command(async)]
pub fn preview_save_imports(paths: Vec<String>) -> Result<Vec<ImportPreview>, String> {
    // One pass over the sidecars for the whole batch. Asking per file
    // would rescan the archive once per file.
    let index = store::hash_index().map_err(|e| err("Could not read the archive", e))?;

    Ok(paths
        .into_iter()
        .map(|raw| {
            let path = PathBuf::from(&raw);
            let file_name = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("savegame.sav")
                .to_string();
            let modified_at_ms = std::fs::metadata(&path)
                .and_then(|m| m.modified())
                .ok()
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| d.as_millis() as u64);

            let mut preview = ImportPreview {
                path: path.display().to_string(),
                file_name,
                file_size: 0,
                modified_at_ms,
                summary: None,
                error: None,
                checksum_valid: false,
                duplicate: None,
            };

            let bytes = match std::fs::read(&path) {
                Ok(bytes) => bytes,
                Err(e) => {
                    preview.error = Some(err("Could not read it", e));
                    return preview;
                }
            };
            preview.file_size = bytes.len() as u64;

            // `parse_unchecked`: a save with a bad checksum is worth
            // keeping a copy of, and the preview says so rather than
            // refusing.
            let save = match SaveFile::parse_unchecked(bytes.clone()) {
                Ok(save) => save,
                Err(e) => {
                    preview.error = Some(err("Not a Spelunky 2 save", e));
                    return preview;
                }
            };

            preview.checksum_valid = save.checksum_valid();
            preview.summary = Some(SaveSummary::from_save(&save));
            preview.duplicate = index
                .get(&store::hash_bytes(&bytes))
                .map(|meta| DuplicateRecord {
                    id: meta.id.clone(),
                    description: meta.description.clone(),
                    taken_at_ms: meta.taken_at_ms,
                    kind: meta.kind,
                });
            preview
        })
        .collect())
}

/// Copies save files into the managed library.
///
/// The originals are left where they are. Importing bytes the archive
/// already holds is allowed: [`preview_save_imports`] reports the
/// duplicate and the user decides, because two copies of one save under
/// different names is a reasonable thing to want.
///
/// A file that fails is recorded and the rest still go in. Stopping at
/// the first failure would leave a partial import the user cannot see the
/// shape of.
#[tauri::command(async)]
pub fn import_saves(items: Vec<ImportItem>) -> Result<ImportOutcome, String> {
    let mut outcome = ImportOutcome {
        imported: Vec::new(),
        failed: Vec::new(),
    };
    for item in items {
        let path = PathBuf::from(&item.path);
        if !path.is_file() {
            outcome.failed.push(ImportFailure {
                path: item.path,
                error: "The file is no longer there.".into(),
            });
            continue;
        }
        // Filed under when the save was last written, so it lands where
        // it belongs in the archive's chronology. A file whose time
        // cannot be read falls back to now.
        let taken_at_ms = std::fs::metadata(&path)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_millis() as u64)
            .unwrap_or_else(store::now_ms);

        match store::capture_at(&path, &item.description, SaveKind::Imported, taken_at_ms) {
            Ok(save) => outcome.imported.push(save),
            Err(e) => outcome.failed.push(ImportFailure {
                path: item.path,
                error: e.to_string(),
            }),
        }
    }
    Ok(outcome)
}

/// Archives the live save into the managed library.
#[tauri::command(async)]
pub fn create_managed_save(description: String) -> Result<StoredSave, String> {
    let path = save_path().ok_or("No Spelunky 2 install directory is configured.")?;
    if !path.exists() {
        return Err(format!("No save file at {}", path.display()));
    }
    store::capture(&path, &description, SaveKind::Manual)
        .map_err(|e| err("Could not archive the save", e))
}

/// Changes an archived save's description, in either library.
#[tauri::command]
pub fn rename_stored_save(id: String, description: String) -> Result<StoredSave, String> {
    store::set_description(&id, &description).map_err(|e| err("Could not rename the save", e))
}

/// Deletes an archived save from either library.
#[tauri::command(async)]
pub fn delete_stored_save(id: String) -> Result<(), String> {
    store::delete(&id).map_err(|e| err("Could not delete the save", e))
}

/// One point on the stats history.
///
/// Deliberately not a whole [`SaveSummary`]. A summary serializes to about
/// 4 KB, most of it the death histogram and the journal breakdown, and the
/// charts plot none of that: they want a handful of scalars per point. At
/// 500 snapshots the full form was a 2 MB payload to draw six lines from.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct HistoryPoint {
    pub id: String,
    pub taken_at_ms: u64,
    pub description: String,
    pub library: Library,
    /// Whether this point still has a save behind it.
    pub restorable: bool,

    pub plays: i32,
    pub deaths: i32,
    /// Normal, hard and Cosmic Ocean wins added together.
    pub wins: i32,
    pub journal_discovered: usize,
    pub score_total: i64,
    pub time_total_millis: i64,
    pub characters_unlocked: u32,
    pub deepest_area: u8,
    pub deepest_level: u8,
}

impl HistoryPoint {
    fn from_stored(stored: &StoredSave) -> Self {
        let summary = &stored.summary;
        Self {
            id: stored.meta.id.clone(),
            taken_at_ms: stored.meta.taken_at_ms,
            description: stored.meta.description.clone(),
            library: stored.library,
            restorable: stored.restorable,
            plays: summary.plays,
            deaths: summary.deaths,
            wins: summary.wins_normal + summary.wins_hard + summary.wins_special,
            journal_discovered: summary.journal_discovered,
            score_total: summary.score_total,
            time_total_millis: summary.time_total_millis,
            characters_unlocked: summary.characters_unlocked,
            deepest_area: summary.deepest_area,
            deepest_level: summary.deepest_level,
        }
    }
}

/// Everything the Stats panel needs from the archive, in one pass.
///
/// The history and the gallery are both built by walking every archived
/// save, and walking one means parsing it. Two separate commands meant
/// doing that twice for a single page load, which at 500 snapshots is not
/// free.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct StatsOverview {
    /// Oldest first, which is the order a time axis wants. The lists in
    /// the manage view are newest first, because that is the order
    /// someone scanning for "the one from yesterday" wants.
    pub history: Vec<HistoryPoint>,
    pub gallery: Vec<GalleryEntry>,
}

/// A save's stats, with its stickers named.
///
/// `ml2_save` reports the sticker entity types raw, since naming them
/// needs the game's entity table rather than the save format. This is
/// where the two meet.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveDetail {
    #[serde(flatten)]
    pub stats: SaveStats,
    pub stickers: Vec<stickers::Sticker>,
}

impl SaveDetail {
    fn new(stats: SaveStats) -> Self {
        Self {
            stickers: stickers::name_stickers(&stats.stickers),
            stats,
        }
    }
}

/// Full per-entry stats for the live save.
///
/// Separate from [`get_save_status`] because it is an order of magnitude
/// bigger: every journal entry, every kill counter, every character. The
/// status card does not need that, and the Stats panel is not always open.
#[tauri::command]
pub fn get_save_stats() -> Result<SaveDetail, String> {
    let path = save_path().ok_or("No Spelunky 2 install directory is configured.")?;
    // Matches `get_save_status`, which also tolerates a bad checksum.
    let bytes = std::fs::read(&path).map_err(|e| err("Could not read the save", e))?;
    let save = SaveFile::parse_unchecked(bytes).map_err(|e| err("Could not read the save", e))?;
    Ok(SaveDetail::new(SaveStats::from_save(&save)))
}

/// Per-entry stats for one archived save, so a snapshot can be inspected
/// without restoring it.
#[tauri::command]
pub fn get_stored_save_stats(id: String) -> Result<SaveDetail, String> {
    let stored = store::get(&id).map_err(|e| err("Could not read the archived save", e))?;
    if !stored.restorable {
        return Err(
            "That snapshot's save file was pruned, so only its summary is available.".into(),
        );
    }
    // `parse_unchecked`, matching the listing: a save whose checksum has
    // rotted still gets a row, so it has to open when that row is clicked.
    let bytes = std::fs::read(&stored.path).map_err(|e| err("Could not read the save", e))?;
    let save = SaveFile::parse_unchecked(bytes).map_err(|e| err("Could not read the save", e))?;
    Ok(SaveDetail::new(SaveStats::from_save(&save)))
}

/// The history and the constellation gallery, from a single walk of the
/// archive.
#[tauri::command(async)]
pub fn get_stats_overview() -> Result<StatsOverview, String> {
    let stored = store::list_all().map_err(|e| err("Could not read the archive", e))?;

    let mut history: Vec<HistoryPoint> = stored.iter().map(HistoryPoint::from_stored).collect();
    history.sort_by_key(|point| point.taken_at_ms);

    Ok(StatsOverview {
        gallery: build_gallery(&stored),
        history,
    })
}

/// One constellation in the gallery.
///
/// A save can hold exactly one constellation, and generating a new one
/// overwrites the last. So the only place an old chart still exists is in
/// whatever was archived while it was current, which is what makes a
/// gallery worth building at all.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct GalleryEntry {
    /// Shape signature, used to group duplicates. Also a stable key.
    pub signature: String,
    pub constellation: Constellation,
    /// When it was first seen, epoch milliseconds.
    pub first_seen_ms: u64,
    /// When it was last seen.
    pub last_seen_ms: u64,
    /// How many archived saves hold this same chart.
    pub occurrences: usize,
    /// An archived save that holds it, for jumping to the record.
    pub source_id: Option<String>,
    /// The description of that save.
    pub description: String,
    /// Whether the live save has this constellation right now.
    pub is_current: bool,
    /// Whether `description` is still an automatic capture's boilerplate,
    /// so a named save can take its place.
    #[serde(skip)]
    pub is_automatic: bool,
}

/// Every distinct constellation across the live save and the archive,
/// newest first.
///
/// Identical charts are collapsed: after a Cosmic Ocean win every
/// subsequent snapshot carries the same one, and a gallery showing it
/// forty times would be useless. Grouping is by shape, so two genuinely
/// different runs that happened to produce similar colors stay separate.
fn build_gallery(stored: &[StoredSave]) -> Vec<GalleryEntry> {
    use std::collections::HashMap;

    // The live save first, so its chart is the one marked current even if
    // an archived copy shares the shape.
    let current = save_path()
        .filter(|p| p.exists())
        .and_then(|p| SaveFile::read(&p).ok())
        .and_then(|save| save.constellation())
        .filter(|c| !c.is_empty());
    let current_signature = current.as_ref().map(|c| c.signature());

    let mut entries: HashMap<String, GalleryEntry> = HashMap::new();

    for record in stored {
        let Some(constellation) = record.summary.constellation.clone() else {
            continue;
        };
        let signature = constellation.signature();
        let taken = record.meta.taken_at_ms;

        entries
            .entry(signature.clone())
            .and_modify(|entry| {
                entry.occurrences += 1;
                entry.first_seen_ms = entry.first_seen_ms.min(taken);
                if taken > entry.last_seen_ms {
                    entry.last_seen_ms = taken;
                }
                // Prefer a description someone actually wrote over an
                // automatic snapshot's boilerplate, which is never empty.
                if record.meta.kind != SaveKind::Automatic
                    && !record.meta.description.is_empty()
                    && (entry.is_automatic || entry.description.is_empty())
                {
                    entry.is_automatic = false;
                    entry.description = record.meta.description.clone();
                    entry.source_id = Some(record.meta.id.clone());
                }
            })
            .or_insert_with(|| GalleryEntry {
                is_current: current_signature.as_deref() == Some(signature.as_str()),
                signature,
                constellation,
                first_seen_ms: taken,
                last_seen_ms: taken,
                occurrences: 1,
                source_id: Some(record.meta.id.clone()),
                description: record.meta.description.clone(),
                is_automatic: record.meta.kind == SaveKind::Automatic,
            });
    }

    // A constellation in the live save that was never archived still
    // belongs in the gallery.
    if let (Some(constellation), Some(signature)) = (current, current_signature) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis() as u64)
            .unwrap_or(0);
        entries
            .entry(signature.clone())
            .and_modify(|entry| entry.is_current = true)
            .or_insert_with(|| GalleryEntry {
                signature,
                constellation,
                first_seen_ms: now,
                last_seen_ms: now,
                occurrences: 0,
                source_id: None,
                description: "Your current save".to_string(),
                is_current: true,
                is_automatic: false,
            });
    }

    let mut gallery: Vec<GalleryEntry> = entries.into_values().collect();
    gallery.sort_by(|a, b| {
        // Current first, then most recent.
        b.is_current
            .cmp(&a.is_current)
            .then_with(|| b.last_seen_ms.cmp(&a.last_seen_ms))
    });
    gallery
}

/// What a retention policy would do to the snapshots already archived.
///
/// The settings UI calls this on every change, so five number fields
/// become "of your 42 snapshots, 18 keep their save file". Nothing is
/// written; this only reports.
#[tauri::command(async)]
pub fn preview_retention(settings: RetentionSettings) -> Result<RetentionPreview, String> {
    let candidates: Vec<retention::Candidate> = store::list(Library::Snapshots)
        .map_err(|e| err("Could not read the snapshots", e))?
        .iter()
        .map(|s| retention::Candidate {
            taken_at_ms: s.meta.taken_at_ms,
            has_save: s.restorable,
        })
        .collect();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0);
    Ok(retention::preview(&settings, now, &candidates))
}

/// Applies the saved retention policy to the snapshot library now.
///
/// Retention otherwise only runs after the snapshotter takes a capture,
/// so changing the policy would appear to do nothing until the next one
/// fired, which at a daily interval could be tomorrow. Returns how many
/// snapshots lost their save file.
#[tauri::command(async)]
pub fn apply_retention_now() -> Result<usize, String> {
    let settings = settings();
    store::apply_retention(&settings.retention).map_err(|e| err("Could not apply retention", e))
}

/// Reports what restoring `id` would change, without changing anything.
///
/// A save that cannot be parsed is treated as nothing to lose rather than
/// as an error: restoring over a corrupt save is precisely the case this
/// feature is for, and refusing to preview it would block the one action
/// the user needs.
#[tauri::command]
pub fn preview_save_restore(id: String) -> Result<RestorePreview, String> {
    let stored = store::get(&id).map_err(|e| err("Could not read the archived save", e))?;

    let current = save_path()
        .filter(|p| p.exists())
        .and_then(|p| SaveFile::read(&p).ok())
        .map(|save| SaveSummary::from_save(&save));

    let (comparison, has_current_save) = match &current {
        Some(current) => (current.compare(&stored.summary), true),
        None => (
            ProgressComparison {
                regressions: Vec::new(),
                advances: Vec::new(),
            },
            false,
        ),
    };

    Ok(RestorePreview {
        loses_progress: comparison.loses_progress(),
        identical: has_current_save && comparison.is_identical(),
        comparison,
        has_current_save,
        stored,
    })
}

/// Restores an archived save over the live one.
///
/// With `backup_first`, the current save is archived as a `PreRestore`
/// record before being replaced, so the restore itself is undoable. That
/// backup is taken *before* the destination is touched: if it fails, the
/// restore does not happen.
#[tauri::command(async)]
pub fn restore_stored_save(id: String, backup_first: bool) -> Result<Option<StoredSave>, String> {
    let stored = store::get(&id).map_err(|e| err("Could not read the archived save", e))?;
    let target = save_path().ok_or("No Spelunky 2 install directory is configured.")?;

    // Verify the archived save before overwriting anything with it.
    let restored = SaveFile::read(&stored.path).map_err(|e| {
        err(
            "The archived save could not be read, so nothing was changed",
            e,
        )
    })?;

    let backup = if backup_first && target.exists() {
        match store::capture(&target, "Replaced by a restore", SaveKind::PreRestore) {
            Ok(backup) => Some(backup),
            Err(store::StoreError::Save(e)) => {
                // The save on disk is unreadable, which is very likely why
                // a restore is happening. Backing it up is impossible;
                // carrying on is what the user asked for.
                tracing::warn!("Could not back up the current save before restoring: {e}");
                None
            }
            Err(e) => return Err(err("Could not back up the current save", e)),
        }
    } else {
        None
    };

    write_atomically(&target, restored.as_bytes())
        .map_err(|e| err("Could not write the save", e))?;
    tracing::info!("Restored archived save {id} to {}", target.display());
    Ok(backup)
}

/// Opens one of the two save folders in the system file manager.
#[tauri::command]
pub fn open_saves_folder<R: tauri::Runtime>(
    app: tauri::AppHandle<R>,
    library: Library,
) -> Result<(), String> {
    use tauri_plugin_opener::OpenerExt;
    let dir =
        store::ensure_library_dir(library).map_err(|e| err("Could not open the folder", e))?;
    app.opener()
        .open_path(dir.to_string_lossy(), None::<&str>)
        .map_err(|e| e.to_string())
}

/// Reads the snapshotter settings.
#[tauri::command]
pub fn get_snapshot_settings() -> SnapshotSettings {
    settings()
}

/// Writes the snapshotter settings.
///
/// The running snapshotter re-reads config on every consideration, so a
/// change takes effect without a restart.
#[tauri::command]
pub fn set_snapshot_settings(settings: SnapshotSettings) -> Result<SnapshotSettings, String> {
    let settings = settings.sanitized();
    crate::config::set_saves_settings(&settings)?;
    Ok(settings)
}

/// Starts the background snapshotter.
pub fn start(app: AppHandle) {
    snapshotter::spawn(app);
}

/// Writes `bytes` to `path` without ever leaving a partial file there.
///
/// The temporary file is created in the destination's own directory so the
/// rename stays on one filesystem, where it is atomic. Writing straight to
/// the target would mean a crash mid-write destroys the save, which is the
/// exact failure this feature is meant to protect people from.
/// Writes `bytes` over `path` via a temporary file and a rename.
///
/// Rename replaces the target atomically on both platforms - Windows via
/// `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`, POSIX via `rename(2)` -
/// so the previous save survives every failure up to the last instant.
/// The target is never deleted first: a delete that succeeds followed by
/// a rename that does not, because the game or a sync client holds the
/// file for a moment, would leave no save at all.
///
/// The temporary name carries the process id and a counter, so two writes
/// in flight at once cannot rename each other's bytes over the target.
fn write_atomically(path: &Path, bytes: &[u8]) -> std::io::Result<()> {
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT: AtomicU64 = AtomicU64::new(0);

    let dir = path.parent().unwrap_or_else(|| Path::new("."));
    std::fs::create_dir_all(dir)?;
    let temp = dir.join(format!(
        ".{}.{}.{}.ml2tmp",
        path.file_name().and_then(|n| n.to_str()).unwrap_or("save"),
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed),
    ));
    std::fs::write(&temp, bytes)?;
    match std::fs::rename(&temp, path) {
        Ok(()) => Ok(()),
        Err(e) => {
            let _ = std::fs::remove_file(&temp);
            Err(e)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn settings_are_clamped_to_something_sane() {
        let settings = SnapshotSettings {
            enabled: true,
            interval_hours: 0,
            retention: RetentionSettings::default(),
        }
        .sanitized();
        assert_eq!(settings.interval_hours, MIN_INTERVAL_HOURS);

        let untouched = SnapshotSettings {
            enabled: true,
            interval_hours: 24,
            retention: RetentionSettings::default(),
        }
        .sanitized();
        assert_eq!(untouched.interval_hours, 24);
    }

    #[test]
    fn defaults_are_opt_in_daily_and_lossless() {
        let settings = SnapshotSettings::default();
        assert!(
            !settings.enabled,
            "snapshotting writes files, so it is opt-in"
        );
        assert_eq!(settings.interval_hours, 24);
        assert!(
            settings.retention.keep_all,
            "pruning by default would quietly cost people their stats history"
        );
    }

    /// A settings object from an older shape must not take the rest of
    /// the config down with it.
    #[test]
    fn an_unreadable_retention_value_falls_back_without_losing_the_rest() {
        let json = r#"{
            "enabled": true,
            "intervalHours": 6,
            "retention": "thinned"
        }"#;
        let settings: SnapshotSettings = serde_json::from_str(json).unwrap();
        assert!(settings.enabled, "the rest of the settings must survive");
        assert_eq!(settings.interval_hours, 6);
        assert!(settings.retention.keep_all, "and retention falls back");
    }

    #[test]
    fn a_missing_retention_value_takes_the_default() {
        let json = r#"{ "enabled": true, "intervalHours": 24 }"#;
        let settings: SnapshotSettings = serde_json::from_str(json).unwrap();
        assert!(settings.retention.keep_all);
    }

    #[test]
    fn atomic_write_replaces_an_existing_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("savegame.sav");
        std::fs::write(&path, b"old contents").unwrap();

        write_atomically(&path, b"new").unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), b"new");

        // No temporary file left behind.
        let strays: Vec<_> = std::fs::read_dir(dir.path())
            .unwrap()
            .flatten()
            .map(|e| e.file_name().to_string_lossy().to_string())
            .filter(|name| name != "savegame.sav")
            .collect();
        assert!(strays.is_empty(), "left behind {strays:?}");
    }

    #[test]
    fn atomic_write_creates_a_missing_file() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("savegame.sav");
        write_atomically(&path, b"fresh").unwrap();
        assert_eq!(std::fs::read(&path).unwrap(), b"fresh");
    }
}
