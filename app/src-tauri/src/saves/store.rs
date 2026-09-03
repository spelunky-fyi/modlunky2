//! On-disk storage for archived saves.
//!
//! Everything lives under the same app-data folder as `config.json`, in
//! two sibling directories:
//!
//! ```text
//! %LOCALAPPDATA%\spelunky.fyi\modlunky2\
//!     saves\                              saves the user made
//!         1756867079123-4f3a9c21.sav
//!         1756867079123-4f3a9c21.json
//!     save-snapshots\                     saves the snapshotter made
//!         1756870679456-90ab12cd.sav
//!         1756870679456-90ab12cd.json
//! ```
//!
//! # Why two directories
//!
//! A save someone stopped to name is not the same kind of thing as one a
//! timer took, and conflating them makes both worse: the list of things
//! you deliberately kept gets buried under machine-generated history, and
//! pruning has to reason about which entries it is allowed to touch.
//!
//! Splitting them puts the retention policy in the path. Anything under
//! `saves` is kept until the user deletes it. Anything under
//! `save-snapshots` is automatic history, and is the only thing retention
//! is ever allowed to touch. Nothing has to inspect a record's kind to
//! know whether pruning may reach it.
//!
//! # Why not the install directory
//!
//! An archived save is insurance against the live one going wrong, so it
//! has to survive the things that go wrong with a game directory: a Steam
//! file verification, a reinstall, or Playlunky sweeping a folder it
//! manages. Keeping them here also means nothing the game or a mod scans
//! ever sees a pile of stray `.sav` files.
//!
//! # What the sidecar holds
//!
//! Only what is not already in the save: the id, when it was taken, the
//! description, why it was taken, and a hash. That is around 340 bytes.
//!
//! Everything a stats view wants - counters, journal progress, the death
//! histogram, the constellation - is derived by parsing the `.sav` when
//! it is listed. Storing that in the sidecar as well measured at 4.2 KB
//! against a 13.9 KB save, so it inflated every snapshot by about 30% to
//! duplicate a file sitting immediately beside it. Parsing a save is a
//! few thousand integer reads, which is cheaper than the disk it saves.
//!
//! Pruning is the one case where the duplication earns its keep. When a
//! `.sav` is removed its summary is written into the sidecar first,
//! because from that moment the sidecar is the only record: the history
//! charts still need the point, and a constellation that was pruned away
//! would otherwise be gone for good. See [`SaveStore::prune_record`].
//!
//! # Identifiers
//!
//! The id is the capture time in epoch milliseconds plus the first four
//! bytes of the save's SHA-256. The timestamp sorts without parsing
//! anything, and the hash both prevents a collision between two captures
//! in the same millisecond and lets the snapshotter skip a save whose
//! bytes have not changed.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use ml2_save::{SaveFile, SaveSummary};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::retention::{Candidate, RetentionSettings, plan_pruning};

/// Which of the two directories a save is filed under.
///
/// This is the retention policy, not just a label: see the module docs.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum Library {
    /// Saves the user made and named. Never pruned.
    Managed,
    /// Automatic history. Pruned oldest-first.
    Snapshots,
}

impl Library {
    /// Both libraries, managed first, which is the order the UI lists them.
    pub const ALL: [Library; 2] = [Library::Managed, Library::Snapshots];

    /// Directory name under the app-data folder.
    const fn dir_name(self) -> &'static str {
        match self {
            Library::Managed => "saves",
            Library::Snapshots => "save-snapshots",
        }
    }
}

/// Why a save was archived.
///
/// The library decides retention; this is for display, and for letting the
/// snapshotter find its own previous captures.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum SaveKind {
    /// The user asked for it, and probably described it.
    Manual,
    /// The snapshotter took it on schedule.
    Automatic,
    /// Taken just before a restore overwrote the live save.
    PreRestore,
    /// Taken just before the editor wrote to the save.
    PreEdit,
    /// Copied in from a save file the user pointed at.
    Imported,
}

impl SaveKind {
    /// Where a save of this kind is filed.
    ///
    /// Pre-restore backups go in the managed library rather than with the
    /// automatic history. The user opted into that copy by choosing to
    /// back up before restoring, and it is the only record of what the
    /// restore replaced, so pruning must never reach it.
    pub const fn library(self) -> Library {
        match self {
            SaveKind::Manual | SaveKind::PreRestore | SaveKind::PreEdit | SaveKind::Imported => {
                Library::Managed
            }
            SaveKind::Automatic => Library::Snapshots,
        }
    }
}

/// What is stored alongside an archived `.sav`.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct StoredSaveMeta {
    /// Identifier, which is also the file stem of both files.
    pub id: String,
    /// Capture time, epoch milliseconds. The frontend formats it.
    pub taken_at_ms: u64,
    /// What the user typed, or a generated note for automatic captures.
    pub description: String,
    /// Why it was archived.
    pub kind: SaveKind,
    /// Where the save was copied from.
    pub source_path: String,
    /// Size of the `.sav` in bytes.
    pub file_size: u64,
    /// Full SHA-256 of the save, for detecting an unchanged file.
    pub sha256: String,
    /// True once pruning has removed the `.sav` and kept only this
    /// record. Defaults to false so records written before this field
    /// existed still load.
    #[serde(default)]
    pub save_pruned: bool,
    /// Stats as of capture, written *only* once the `.sav` is gone.
    ///
    /// While the save exists this stays absent and the summary is derived
    /// from the save instead. Caching it here would add about 5.4 KB to a
    /// 635-byte record beside a 13.8 KB save, a third more disk per
    /// snapshot, and would replace a binary read at fixed offsets with a
    /// larger JSON deserialize that is not obviously cheaper.
    ///
    /// Named apart from `StoredSave::summary` on the wire because that
    /// struct flattens this one: two fields called `summary` would emit a
    /// duplicate JSON key.
    #[serde(
        rename = "prunedSummary",
        default,
        skip_serializing_if = "Option::is_none"
    )]
    pub summary: Option<SaveSummary>,
}

/// An archived save as the frontend sees it.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct StoredSave {
    #[serde(flatten)]
    pub meta: StoredSaveMeta,
    /// Which library it is filed under.
    pub library: Library,
    /// Absolute path of the archived `.sav`. Empty once pruned.
    pub path: String,
    /// Whether this can still be restored. False for a history-only
    /// record whose `.sav` has been pruned away.
    pub restorable: bool,
    /// Stats for this save: parsed from the `.sav` when there is one,
    /// otherwise read back from the sidecar it was baked into at prune
    /// time. Always present either way.
    pub summary: SaveSummary,
}

/// Errors from the save store.
#[derive(Debug, thiserror::Error)]
pub enum StoreError {
    #[error("could not work out where to keep archived saves")]
    NoStorageDir,
    #[error("{0}")]
    Io(String),
    #[error("no archived save with id {0}")]
    NotFound(String),
    #[error("{0}")]
    Save(#[from] ml2_save::SaveError),
}

type Result<T> = std::result::Result<T, StoreError>;

fn io(context: &str, err: std::io::Error) -> StoreError {
    StoreError::Io(format!("{context}: {err}"))
}

fn hash_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

pub fn now_ms() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

// Counts listings, so a test can assert that a loop does not hide one.
// Per-thread because the harness runs tests in parallel and a shared
// counter would see every other test's listings.
#[cfg(test)]
thread_local! {
    static LISTINGS: std::cell::Cell<usize> = const { std::cell::Cell::new(0) };
}

/// Builds the id: sortable timestamp, then a hash prefix so two captures
/// in the same millisecond cannot collide.
impl SaveStore {
    /// A timestamp and id safe to write these bytes under.
    ///
    /// Reuses the id when the record already there holds the same save,
    /// so re-importing a file replaces its own record instead of adding a
    /// second copy. Moves along only when the id is taken by different
    /// bytes, which would otherwise be one save silently destroying
    /// another.
    fn free_id(&self, dir: &Path, from: u64, sha256: &str) -> (u64, String) {
        let mut taken_at_ms = from;
        loop {
            let id = make_id(taken_at_ms, sha256);
            let sidecar = dir.join(format!("{id}.json"));
            let occupant = std::fs::read_to_string(&sidecar)
                .ok()
                .and_then(|raw| serde_json::from_str::<StoredSaveMeta>(&raw).ok());
            match occupant {
                // Free, unreadable (an orphan worth replacing), or the
                // same save coming back.
                None => return (taken_at_ms, id),
                Some(meta) if meta.sha256 == sha256 => return (taken_at_ms, id),
                Some(_) => taken_at_ms += 1,
            }
        }
    }
}

fn make_id(taken_at_ms: u64, sha256: &str) -> String {
    format!("{taken_at_ms}-{}", &sha256[..8])
}

/// Whether `id` is one this store could have written.
///
/// Ids arrive from the frontend and are pasted straight into a file name,
/// so anything with a separator or a `..` in it would reach outside the
/// library. Rather than sanitizing, only the shape `make_id` produces is
/// accepted: digits, a hyphen, then hex.
fn is_valid_id(id: &str) -> bool {
    let Some((taken, hash)) = id.split_once('-') else {
        return false;
    };
    !taken.is_empty()
        && taken.bytes().all(|b| b.is_ascii_digit())
        && !hash.is_empty()
        && hash.bytes().all(|b| b.is_ascii_hexdigit())
}

fn write_meta(dir: &Path, meta: &StoredSaveMeta) -> Result<()> {
    let path = dir.join(format!("{}.json", meta.id));
    let json = serde_json::to_string_pretty(meta)
        .map_err(|e| StoreError::Io(format!("encoding save metadata: {e}")))?;
    std::fs::write(&path, json).map_err(|e| io(&format!("writing {}", path.display()), e))
}

/// The two save libraries under one root directory.
///
/// The root is held rather than looked up inside each call, so the store
/// can be pointed at a temporary directory. Everything in here can lose
/// someone's archive, which makes it worth exercising against a real
/// filesystem instead of only in production.
#[derive(Debug, Clone)]
pub struct SaveStore {
    root: PathBuf,
}

impl SaveStore {
    /// A store rooted at `root`, which holds the two library folders.
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    /// The store in the app-data folder, beside `config.json`.
    pub fn default_location() -> Result<Self> {
        let config = crate::config::config_path().ok_or(StoreError::NoStorageDir)?;
        let root = config.parent().ok_or(StoreError::NoStorageDir)?;
        Ok(Self::new(root))
    }

    /// Where a library's saves are kept.
    pub fn library_dir(&self, library: Library) -> PathBuf {
        self.root.join(library.dir_name())
    }

    /// Returns a library's directory, creating it if it is not there yet.
    pub fn ensure_library_dir(&self, library: Library) -> Result<PathBuf> {
        let dir = self.library_dir(library);
        std::fs::create_dir_all(&dir).map_err(|e| io(&format!("creating {}", dir.display()), e))?;
        Ok(dir)
    }

    /// Copies `source` into the library its kind belongs to.
    ///
    /// The save is parsed before anything is written, so a file that is
    /// not a save at all is refused rather than archived. A bad checksum
    /// is not grounds for refusal: that save is the one most worth having
    /// a copy of.
    pub fn capture(&self, source: &Path, description: &str, kind: SaveKind) -> Result<StoredSave> {
        self.capture_at(source, description, kind, now_ms())
    }

    /// Copies `source` in, filed under a time of the caller's choosing.
    ///
    /// An import passes the file's own modification time rather than the
    /// moment it was imported. A save from two years ago belongs two
    /// years back in the list, not at the top under today's heading -
    /// the chronology is the reason for importing it.
    pub fn capture_at(
        &self,
        source: &Path,
        description: &str,
        kind: SaveKind,
        taken_at_ms: u64,
    ) -> Result<StoredSave> {
        let bytes =
            std::fs::read(source).map_err(|e| io(&format!("reading {}", source.display()), e))?;
        // `parse_unchecked`: a save whose checksum has rotted is exactly
        // the one worth keeping a copy of before touching it, and the
        // editor takes a backup before every write. Refusing here would
        // block repairing the save this feature exists to repair. The
        // summary records the damage.
        let save = SaveFile::parse_unchecked(bytes.clone())?;
        let summary = SaveSummary::from_save(&save);

        let library = kind.library();
        let dir = self.ensure_library_dir(library)?;
        let sha256 = hash_hex(&bytes);
        // The id is the timestamp and a hash prefix, so the same file
        // imported twice lands on the same id and simply replaces its own
        // record. That is the point: importing a folder twice leaves one
        // copy of each save rather than two.
        //
        // The exception is a collision between *different* saves, which
        // needs the same millisecond and the same 32 bits of hash. Vanishly
        // unlikely, and silent data loss if it happened, so the id moves
        // along rather than overwriting a record that is not this save.
        let (taken_at_ms, id) = self.free_id(&dir, taken_at_ms, &sha256);

        let meta = StoredSaveMeta {
            taken_at_ms,
            description: description.trim().to_string(),
            kind,
            source_path: source.display().to_string(),
            file_size: bytes.len() as u64,
            sha256,
            save_pruned: false,
            // Absent while the save is here to be parsed.
            summary: None,
            id: id.clone(),
        };

        // The `.sav` lands first. A crash between the two leaves an orphan
        // save with no sidecar, which `list` skips; the other order would
        // leave a sidecar promising a save that is not there.
        let sav_path = dir.join(format!("{id}.sav"));
        std::fs::write(&sav_path, &bytes)
            .map_err(|e| io(&format!("writing {}", sav_path.display()), e))?;
        write_meta(&dir, &meta)?;

        Ok(StoredSave {
            path: sav_path.display().to_string(),
            library,
            restorable: true,
            summary,
            meta,
        })
    }

    /// Whether any record in either library already holds this content.
    ///
    /// Reads only the sidecars. The snapshotter asks this on every change
    /// to the save file, and the answer is a string already sitting in
    /// each record's metadata - parsing every `.sav` to find it would make
    /// a routine check cost the whole archive.
    pub fn contains_hash(&self, sha256: &str) -> Result<bool> {
        Ok(self.find_by_hash(sha256)?.is_some())
    }

    /// Every content hash in the archive, mapped to the record holding it.
    ///
    /// One pass over the sidecars, for callers checking many files at
    /// once: asking [`Self::find_by_hash`] per file would rescan the
    /// whole archive per file.
    pub fn hash_index(&self) -> Result<HashMap<String, StoredSaveMeta>> {
        let mut index = HashMap::new();
        for library in Library::ALL {
            let dir = self.library_dir(library);
            if !dir.exists() {
                continue;
            }
            let Ok(entries) = std::fs::read_dir(&dir) else {
                continue;
            };
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) != Some("json") {
                    continue;
                }
                let Ok(contents) = std::fs::read_to_string(&path) else {
                    continue;
                };
                match serde_json::from_str::<StoredSaveMeta>(&contents) {
                    Ok(meta) => {
                        index.entry(meta.sha256.clone()).or_insert(meta);
                    }
                    Err(err) => {
                        tracing::warn!("Skipping malformed record {}: {err}", path.display())
                    }
                }
            }
        }
        Ok(index)
    }

    /// The record already holding this content, if there is one.
    ///
    /// Reads only the sidecars, for the same reason as
    /// [`Self::contains_hash`]: the hash is right there in the metadata.
    pub fn find_by_hash(&self, sha256: &str) -> Result<Option<StoredSaveMeta>> {
        for library in Library::ALL {
            let dir = self.library_dir(library);
            if !dir.exists() {
                continue;
            }
            let Ok(entries) = std::fs::read_dir(&dir) else {
                continue;
            };
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) != Some("json") {
                    continue;
                }
                let Ok(contents) = std::fs::read_to_string(&path) else {
                    continue;
                };
                match serde_json::from_str::<StoredSaveMeta>(&contents) {
                    Ok(meta) if meta.sha256 == sha256 => return Ok(Some(meta)),
                    Ok(_) => {}
                    Err(err) => {
                        tracing::warn!("Skipping malformed record {}: {err}", path.display())
                    }
                }
            }
        }
        Ok(None)
    }

    /// Re-records a stored save whose file has been rewritten in place.
    ///
    /// The editor can write to an archived save, which leaves the
    /// sidecar's hash and size describing bytes that are no longer there.
    /// A stale hash is not cosmetic: the snapshotter decides whether to
    /// capture by comparing the live save against every recorded hash, so
    /// one that lies can skip a snapshot that should have been taken.
    pub fn record_edit(&self, id: &str, bytes: &[u8]) -> Result<()> {
        let mut stored = self.get(id)?;
        stored.meta.sha256 = hash_hex(bytes);
        stored.meta.file_size = bytes.len() as u64;
        write_meta(&self.library_dir(stored.library), &stored.meta)
    }

    /// Everything in one library, newest first.
    ///
    /// A record that cannot be read is skipped with a warning rather than
    /// failing the whole listing: one bad file should not hide the rest.
    /// Turns one sidecar's metadata into a record.
    ///
    /// `None` for a record that should not be listed at all: the crash
    /// window in `capture`, or a save too damaged to summarize with no
    /// baked-in summary to fall back on. Both are logged.
    fn load_record(
        &self,
        dir: &Path,
        library: Library,
        meta: StoredSaveMeta,
    ) -> Option<StoredSave> {
        let sav_path = dir.join(format!("{}.sav", meta.id));
        let has_save = sav_path.exists();
        if !has_save && !meta.save_pruned {
            // A sidecar with no save and no pruning mark is the crash
            // window in `capture`, not something to show.
            tracing::warn!("Record {} has no .sav beside it; skipping", meta.id);
            return None;
        }

        let derived = if has_save {
            // `parse_unchecked`, not `parse`: an archived save whose
            // checksum has rotted is exactly what someone comes here
            // looking for, so it still gets listed. The summary records
            // the damage rather than the row vanishing.
            match std::fs::read(&sav_path).map(SaveFile::parse_unchecked) {
                Ok(Ok(save)) => Some(SaveSummary::from_save(&save)),
                Ok(Err(err)) => {
                    tracing::warn!("Archived save {} could not be parsed: {err}", meta.id);
                    None
                }
                Err(err) => {
                    tracing::warn!("Archived save {} could not be read: {err}", meta.id);
                    None
                }
            }
        } else {
            None
        };

        // Falls back to the baked-in summary for a pruned record, and
        // also for a save too damaged to parse at all.
        let Some(summary) = derived.or_else(|| meta.summary.clone()) else {
            tracing::warn!("Record {} has no usable stats; skipping", meta.id);
            return None;
        };

        Some(StoredSave {
            path: if has_save {
                sav_path.display().to_string()
            } else {
                String::new()
            },
            library,
            restorable: has_save,
            summary,
            meta,
        })
    }

    pub fn list(&self, library: Library) -> Result<Vec<StoredSave>> {
        #[cfg(test)]
        LISTINGS.with(|n| n.set(n.get() + 1));
        let started = std::time::Instant::now();
        let dir = self.library_dir(library);
        if !dir.exists() {
            return Ok(Vec::new());
        }
        let entries =
            std::fs::read_dir(&dir).map_err(|e| io(&format!("reading {}", dir.display()), e))?;

        let mut saves = Vec::new();
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            let contents = match std::fs::read_to_string(&path) {
                Ok(c) => c,
                Err(err) => {
                    tracing::warn!("Skipping unreadable record {}: {err}", path.display());
                    continue;
                }
            };
            let meta: StoredSaveMeta = match serde_json::from_str(&contents) {
                Ok(m) => m,
                Err(err) => {
                    tracing::warn!("Skipping malformed record {}: {err}", path.display());
                    continue;
                }
            };

            if let Some(record) = self.load_record(&dir, library, meta) {
                saves.push(record);
            }
        }
        saves.sort_by(|a, b| b.meta.taken_at_ms.cmp(&a.meta.taken_at_ms));
        // Listing cost scales with the archive, and the archive grows on
        // its own, so this is worth being able to see. Measured at ~310ms
        // for 533 saves in a debug build; release is a good deal faster.
        tracing::debug!(
            "Listed {} saves from {library:?} in {:?}",
            saves.len(),
            started.elapsed()
        );
        Ok(saves)
    }

    /// Everything in both libraries, newest first.
    pub fn list_all(&self) -> Result<Vec<StoredSave>> {
        let mut all = Vec::new();
        for library in Library::ALL {
            all.extend(self.list(library)?);
        }
        all.sort_by(|a, b| b.meta.taken_at_ms.cmp(&a.meta.taken_at_ms));
        Ok(all)
    }

    /// One archived save by id, from whichever library holds it.
    ///
    /// Ids carry no hint of their library, so callers never have to know
    /// which one a record is in to act on it.
    /// Reads one record by id.
    ///
    /// Goes straight to `<id>.json`. Searching a listing instead would be
    /// O(n) - listing parses every save in the archive - and pruning
    /// fetches one record per save, so retention would be O(n^2).
    pub fn get(&self, id: &str) -> Result<StoredSave> {
        if !is_valid_id(id) {
            return Err(StoreError::NotFound(id.to_string()));
        }
        for library in Library::ALL {
            let dir = self.library_dir(library);
            let path = dir.join(format!("{id}.json"));
            let Ok(contents) = std::fs::read_to_string(&path) else {
                continue;
            };
            let meta: StoredSaveMeta = match serde_json::from_str(&contents) {
                Ok(meta) => meta,
                Err(err) => {
                    tracing::warn!("Malformed record {}: {err}", path.display());
                    continue;
                }
            };
            if let Some(found) = self.load_record(&dir, library, meta) {
                return Ok(found);
            }
        }
        Err(StoreError::NotFound(id.to_string()))
    }

    /// Deletes an archived save and its sidecar.
    pub fn delete(&self, id: &str) -> Result<()> {
        let stored = self.get(id)?;
        let dir = self.library_dir(stored.library);
        // Remove the sidecar first so a failure partway through leaves an
        // orphan `.sav` (invisible to `list`) rather than a sidecar
        // pointing at a save that is gone.
        let meta_path = dir.join(format!("{id}.json"));
        std::fs::remove_file(&meta_path)
            .map_err(|e| io(&format!("deleting {}", meta_path.display()), e))?;
        if !stored.path.is_empty()
            && let Err(err) = std::fs::remove_file(&stored.path)
            && err.kind() != std::io::ErrorKind::NotFound
        {
            return Err(io(&format!("deleting {}", stored.path), err));
        }
        Ok(())
    }

    /// Changes an archived save's description.
    pub fn set_description(&self, id: &str, description: &str) -> Result<StoredSave> {
        let mut stored = self.get(id)?;
        let dir = self.library_dir(stored.library);
        stored.meta.description = description.trim().to_string();
        write_meta(&dir, &stored.meta)?;
        Ok(stored)
    }

    /// Removes the `.sav` from a record, keeping the sidecar.
    ///
    /// The record stays in the listing as history: its summary is still a
    /// point on every stats chart, and its constellation still shows in
    /// the gallery. It just cannot be restored any more.
    ///
    /// This is where the summary gets written into the sidecar. Until now
    /// it was derived from the save on demand; from here on the sidecar is
    /// the only copy, so it has to hold one.
    /// Drops a record's `.sav`, keeping everything the record knows.
    ///
    /// Takes the record rather than an id: retention holds the whole list
    /// already, and making it re-fetch each one by id is what put a full
    /// listing back inside the loop and made pruning quadratic.
    pub fn prune_record(&self, mut stored: StoredSave) -> Result<()> {
        if !stored.restorable {
            return Ok(());
        }
        let dir = self.library_dir(stored.library);

        // Bake the stats in and mark the record in one write. If the
        // process dies between this and the delete, the record reads as
        // pruned and its missing save agrees; the other order would leave
        // a record claiming a save that is gone.
        stored.meta.save_pruned = true;
        stored.meta.summary = Some(stored.summary.clone());
        write_meta(&dir, &stored.meta)?;

        if let Err(err) = std::fs::remove_file(&stored.path)
            && err.kind() != std::io::ErrorKind::NotFound
        {
            return Err(io(&format!("deleting {}", stored.path), err));
        }
        Ok(())
    }

    /// Applies a retention policy to the snapshot library.
    ///
    /// Returns how many saves were pruned. Nothing is ever deleted
    /// outright; see [`SaveStore::prune_record`].
    pub fn apply_retention(&self, settings: &RetentionSettings) -> Result<usize> {
        let snapshots = self.list(Library::Snapshots)?;
        let candidates: Vec<Candidate> = snapshots
            .iter()
            .map(|s| Candidate {
                taken_at_ms: s.meta.taken_at_ms,
                has_save: s.restorable,
            })
            .collect();

        // Taken out by index rather than removed, so the plan's indices
        // stay meaningful however many have already been used.
        let mut snapshots: Vec<Option<StoredSave>> = snapshots.into_iter().map(Some).collect();
        let mut pruned = 0;
        for index in plan_pruning(settings, now_ms(), &candidates) {
            let Some(record) = snapshots.get_mut(index).and_then(Option::take) else {
                continue;
            };
            let id = record.meta.id.clone();
            match self.prune_record(record) {
                Ok(()) => pruned += 1,
                Err(err) => tracing::warn!("Could not prune snapshot {id}: {err}"),
            }
        }
        Ok(pruned)
    }

    /// SHA-256 of a file, without keeping the contents around.
    pub fn hash_file(path: &Path) -> Result<String> {
        let bytes =
            std::fs::read(path).map_err(|e| io(&format!("reading {}", path.display()), e))?;
        Ok(hash_hex(&bytes))
    }
}

// --- Convenience wrappers ----------------------------------------------------
//
// The commands and the snapshotter always want the store in the real
// app-data folder, and saying so at every call site would be noise.

fn store() -> Result<SaveStore> {
    SaveStore::default_location()
}

pub fn capture(source: &Path, description: &str, kind: SaveKind) -> Result<StoredSave> {
    store()?.capture(source, description, kind)
}

pub fn list(library: Library) -> Result<Vec<StoredSave>> {
    store()?.list(library)
}

pub fn list_all() -> Result<Vec<StoredSave>> {
    store()?.list_all()
}

pub fn get(id: &str) -> Result<StoredSave> {
    store()?.get(id)
}

pub fn delete(id: &str) -> Result<()> {
    store()?.delete(id)
}

pub fn set_description(id: &str, description: &str) -> Result<StoredSave> {
    store()?.set_description(id, description)
}

pub fn apply_retention(settings: &RetentionSettings) -> Result<usize> {
    store()?.apply_retention(settings)
}

pub fn contains_hash(sha256: &str) -> Result<bool> {
    store()?.contains_hash(sha256)
}

pub fn hash_index() -> Result<HashMap<String, StoredSaveMeta>> {
    store()?.hash_index()
}

pub fn capture_at(
    source: &Path,
    description: &str,
    kind: SaveKind,
    taken_at_ms: u64,
) -> Result<StoredSave> {
    store()?.capture_at(source, description, kind, taken_at_ms)
}

pub fn record_edit(id: &str, bytes: &[u8]) -> Result<()> {
    store()?.record_edit(id, bytes)
}

pub fn ensure_library_dir(library: Library) -> Result<PathBuf> {
    store()?.ensure_library_dir(library)
}

pub fn hash_file(path: &Path) -> Result<String> {
    SaveStore::hash_file(path)
}

/// The content hash of bytes already in hand.
pub fn hash_bytes(bytes: &[u8]) -> String {
    hash_hex(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A minimal but valid v30 save, so `capture` accepts it.
    fn write_save(path: &Path, plays: i32) {
        let mut bytes = vec![0u8; 13862];
        bytes[0..2].copy_from_slice(&30u16.to_le_bytes());
        bytes[ml2_save::layout::PLAYS..ml2_save::layout::PLAYS + 4]
            .copy_from_slice(&plays.to_le_bytes());
        // `capture` verifies the checksum, so it has to be right.
        let end = bytes.len() - 4;
        let crc = !crc32fast::hash(&bytes[2..end]);
        bytes[end..].copy_from_slice(&crc.to_le_bytes());
        std::fs::write(path, bytes).unwrap();
    }

    struct Fixture {
        _dir: tempfile::TempDir,
        store: SaveStore,
        save: PathBuf,
    }

    fn fixture() -> Fixture {
        let dir = tempfile::tempdir().unwrap();
        let save = dir.path().join("savegame.sav");
        write_save(&save, 100);
        Fixture {
            store: SaveStore::new(dir.path().join("data")),
            save,
            _dir: dir,
        }
    }

    #[test]
    fn capture_writes_a_save_and_a_sidecar() {
        let f = fixture();
        let stored = f
            .store
            .capture(&f.save, "  a description  ", SaveKind::Manual)
            .unwrap();

        assert_eq!(
            stored.meta.description, "a description",
            "whitespace is trimmed"
        );
        assert_eq!(stored.library, Library::Managed);
        assert!(stored.restorable);
        assert_eq!(stored.summary.plays, 100);
        assert!(Path::new(&stored.path).exists());
    }

    /// The point of deriving rather than storing: while the save is there,
    /// the sidecar must not carry a copy of what the save already says.
    #[test]
    fn sidecar_holds_no_summary_while_the_save_exists() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Manual).unwrap();

        let sidecar = f
            .store
            .library_dir(Library::Managed)
            .join(format!("{}.json", stored.meta.id));
        let raw = std::fs::read_to_string(&sidecar).unwrap();
        assert!(
            !raw.contains("prunedSummary"),
            "sidecar duplicated what the save already holds"
        );

        // ...and it is tiny next to the save it describes.
        let sidecar_len = raw.len() as u64;
        assert!(
            sidecar_len < stored.meta.file_size / 10,
            "sidecar is {sidecar_len} bytes against a {} byte save",
            stored.meta.file_size
        );

        // ...while the summary is still available, derived from the save.
        assert_eq!(f.store.get(&stored.meta.id).unwrap().summary.plays, 100);
    }

    /// Pruning is the moment the sidecar has to start carrying the stats,
    /// because it becomes the only record.
    #[test]
    fn pruning_keeps_the_stats_and_drops_the_save() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Automatic).unwrap();
        let sav_path = stored.path.clone();

        prune(&f.store, &stored.meta.id);

        assert!(!Path::new(&sav_path).exists(), "the save should be gone");
        let after = f.store.get(&stored.meta.id).unwrap();
        assert!(!after.restorable);
        assert!(after.meta.save_pruned);
        assert_eq!(
            after.summary.plays, 100,
            "the history point has to survive the save"
        );
        assert!(after.path.is_empty());
    }

    #[test]
    fn pruning_twice_is_harmless() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Automatic).unwrap();
        prune(&f.store, &stored.meta.id);
        prune(&f.store, &stored.meta.id);
        assert!(!f.store.get(&stored.meta.id).unwrap().restorable);
    }

    #[test]
    fn kinds_land_in_the_right_libraries() {
        let f = fixture();
        f.store.capture(&f.save, "m", SaveKind::Manual).unwrap();
        write_save(&f.save, 101);
        f.store.capture(&f.save, "p", SaveKind::PreRestore).unwrap();
        write_save(&f.save, 102);
        f.store.capture(&f.save, "a", SaveKind::Automatic).unwrap();

        assert_eq!(f.store.list(Library::Managed).unwrap().len(), 2);
        assert_eq!(f.store.list(Library::Snapshots).unwrap().len(), 1);
        assert_eq!(f.store.list_all().unwrap().len(), 3);
    }

    /// Retention must never be able to reach the managed library, whatever
    /// it is set to.
    #[test]
    fn retention_only_touches_snapshots() {
        let f = fixture();
        let manual = f
            .store
            .capture(&f.save, "keep me", SaveKind::Manual)
            .unwrap();
        write_save(&f.save, 101);
        let auto = f
            .store
            .capture(&f.save, "auto", SaveKind::Automatic)
            .unwrap();

        // Every tier off, so only the newest snapshot survives. Both
        // captures land in the same hour, so this is the sharpest test of
        // "retention cannot reach the managed library".
        let aggressive = RetentionSettings {
            keep_all: false,
            policy: super::super::retention::RetentionPolicy {
                hourly: 0,
                daily: 0,
                weekly: 0,
                monthly: 0,
                yearly: 0,
            },
        };

        write_save(&f.save, 102);
        let newer = f
            .store
            .capture(&f.save, "auto2", SaveKind::Automatic)
            .unwrap();

        let pruned = f.store.apply_retention(&aggressive).unwrap();
        assert_eq!(pruned, 1, "the older of the two snapshots loses its save");
        assert!(f.store.get(&newer.meta.id).unwrap().restorable);
        assert!(!f.store.get(&auto.meta.id).unwrap().restorable);
        assert!(
            f.store.get(&manual.meta.id).unwrap().restorable,
            "a save the user made must never be pruned"
        );
    }

    #[test]
    fn keeping_everything_prunes_nothing() {
        let f = fixture();
        let auto = f
            .store
            .capture(&f.save, "auto", SaveKind::Automatic)
            .unwrap();
        assert_eq!(
            f.store
                .apply_retention(&RetentionSettings::default())
                .unwrap(),
            0
        );
        assert!(f.store.get(&auto.meta.id).unwrap().restorable);
    }

    #[test]
    fn delete_removes_both_files() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Manual).unwrap();
        let sav_path = stored.path.clone();
        let sidecar = f
            .store
            .library_dir(Library::Managed)
            .join(format!("{}.json", stored.meta.id));

        f.store.delete(&stored.meta.id).unwrap();
        assert!(!Path::new(&sav_path).exists());
        assert!(!sidecar.exists());
        assert!(f.store.get(&stored.meta.id).is_err());
    }

    #[test]
    fn a_pruned_record_can_still_be_deleted() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Automatic).unwrap();
        prune(&f.store, &stored.meta.id);
        f.store.delete(&stored.meta.id).unwrap();
        assert!(f.store.get(&stored.meta.id).is_err());
    }

    #[test]
    fn renaming_keeps_everything_else() {
        let f = fixture();
        let stored = f
            .store
            .capture(&f.save, "before", SaveKind::Manual)
            .unwrap();
        let renamed = f.store.set_description(&stored.meta.id, " after ").unwrap();
        assert_eq!(renamed.meta.description, "after");

        let reread = f.store.get(&stored.meta.id).unwrap();
        assert_eq!(reread.summary.plays, 100);
        assert!(reread.restorable);
    }

    #[test]
    fn listing_is_newest_first() {
        let f = fixture();
        f.store.capture(&f.save, "1", SaveKind::Manual).unwrap();
        write_save(&f.save, 101);
        f.store.capture(&f.save, "2", SaveKind::Manual).unwrap();

        let listed = f.store.list(Library::Managed).unwrap();
        assert_eq!(listed.len(), 2);
        assert!(listed[0].meta.taken_at_ms >= listed[1].meta.taken_at_ms);
    }

    #[test]
    fn refuses_to_archive_something_that_is_not_a_save() {
        let f = fixture();
        let junk = f.save.with_file_name("junk.sav");
        std::fs::write(&junk, b"not a save").unwrap();
        assert!(f.store.capture(&junk, "x", SaveKind::Manual).is_err());
        assert!(f.store.list(Library::Managed).unwrap().is_empty());
    }

    /// A save whose checksum has rotted is exactly what someone comes to
    /// the archive to replace, so it must still appear in the listing.
    #[test]
    fn a_corrupt_archived_save_still_lists() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Manual).unwrap();

        let mut bytes = std::fs::read(&stored.path).unwrap();
        bytes[ml2_save::layout::PLAYS] ^= 0xff;
        std::fs::write(&stored.path, bytes).unwrap();

        let listed = f.store.get(&stored.meta.id).unwrap();
        assert!(listed.restorable);
        assert!(
            !listed.summary.checksum_valid,
            "the listing should report the damage rather than hide the row"
        );
    }

    #[test]
    fn an_empty_store_lists_nothing() {
        let f = fixture();
        assert!(f.store.list(Library::Managed).unwrap().is_empty());
        assert!(f.store.list_all().unwrap().is_empty());
        assert!(f.store.get("nope").is_err());
    }

    /// An orphan `.sav` with no sidecar is the crash window in `capture`.
    /// It must not show up as a record.
    #[test]
    fn an_orphan_save_is_ignored() {
        let f = fixture();
        let dir = f.store.ensure_library_dir(Library::Managed).unwrap();
        std::fs::copy(&f.save, dir.join("999-deadbeef.sav")).unwrap();
        assert!(f.store.list(Library::Managed).unwrap().is_empty());
    }

    #[test]
    fn ids_sort_by_time_and_survive_a_collision() {
        let a = make_id(1_000, "abcdef0123456789");
        let b = make_id(2_000, "abcdef0123456789");
        assert!(a < b, "later captures must sort later");
        assert_ne!(a, make_id(1_000, "99887766abcdef00"));
    }

    /// The library a kind lands in is what decides whether pruning can
    /// ever reach it, so it is worth stating outright.
    #[test]
    fn only_automatic_saves_land_in_the_prunable_library() {
        assert_eq!(SaveKind::Automatic.library(), Library::Snapshots);
        assert_eq!(SaveKind::Manual.library(), Library::Managed);
        assert_eq!(
            SaveKind::PreRestore.library(),
            Library::Managed,
            "the copy taken before a restore is the only record of what it replaced"
        );
    }

    #[test]
    fn libraries_have_distinct_directories() {
        assert_ne!(Library::Managed.dir_name(), Library::Snapshots.dir_name());
        assert_eq!(Library::Managed.dir_name(), "saves");
        assert_eq!(Library::Snapshots.dir_name(), "save-snapshots");
    }

    /// An id from the frontend is pasted straight into a file name, so
    /// anything that could climb out of the library has to be refused
    /// before it reaches the filesystem.
    #[test]
    fn ids_that_are_not_ours_are_refused() {
        assert!(is_valid_id("1756867079123-4f3a9c21"));
        assert!(!is_valid_id("../../../etc/passwd"));
        assert!(!is_valid_id("1756867079123-4f3a9c21/../../x"));
        assert!(!is_valid_id(r"..\windows\system32"));
        assert!(!is_valid_id(""));
        assert!(!is_valid_id("-abc"));
        assert!(!is_valid_id("123-"));
        assert!(!is_valid_id("123-zzzz"), "not hex");
        assert!(!is_valid_id("abc-123"), "timestamp must be digits");

        let f = fixture();
        assert!(f.store.get("../../../etc/passwd").is_err());
    }

    /// Applying a retention policy must list the archive once, not once
    /// per save.
    ///
    /// A listing parses every save in the library, so fetching each
    /// record by id inside the prune loop makes retention quadratic. The
    /// counter is the only way to assert that without timing, which on a
    /// shared machine cannot tell 2x from 4x reliably.
    #[test]
    fn retention_lists_the_archive_once() {
        let f = fixture();
        for i in 0..12 {
            write_save(&f.save, 1000 + i);
            f.store
                .capture(&f.save, "auto", SaveKind::Automatic)
                .unwrap();
        }

        let settings = RetentionSettings {
            keep_all: false,
            policy: crate::saves::retention::RetentionPolicy {
                hourly: 1,
                daily: 0,
                weekly: 0,
                monthly: 0,
                yearly: 0,
            },
        };
        let before = LISTINGS.with(std::cell::Cell::get);
        let pruned = f.store.apply_retention(&settings).unwrap();
        let listings = LISTINGS.with(std::cell::Cell::get) - before;

        assert!(pruned >= 11, "pruned {pruned} of 12");
        assert_eq!(listings, 1, "one listing, whatever the archive holds");
    }

    /// An imported save is the user's, so it belongs beside the ones they
    /// archived by hand rather than in the automatic history a retention
    /// policy is allowed to thin.
    #[test]
    fn an_imported_save_lands_in_the_managed_library() {
        assert_eq!(SaveKind::Imported.library(), Library::Managed);

        let f = fixture();
        let stored = f
            .store
            .capture(&f.save, "from my install", SaveKind::Imported)
            .unwrap();
        assert_eq!(stored.library, Library::Managed);
        assert!(f.store.list(Library::Snapshots).unwrap().is_empty());

        // The original is copied, not moved.
        assert!(
            f.save.exists(),
            "the file the user pointed at is still there"
        );
    }

    /// Importing the same file twice must leave one record, not two.
    ///
    /// An import is filed under the file's own modification time, so the
    /// same bytes and the same time give the same id and the record
    /// replaces itself. Re-importing a folder is then a no-op rather than
    /// a way to double the archive.
    #[test]
    fn re_importing_a_file_replaces_its_own_record() {
        let f = fixture();
        let when = 1_700_000_000_000;

        let first = f
            .store
            .capture_at(&f.save, "old save", SaveKind::Imported, when)
            .unwrap();
        let again = f
            .store
            .capture_at(&f.save, "old save again", SaveKind::Imported, when)
            .unwrap();

        assert_eq!(first.meta.id, again.meta.id);
        assert_eq!(f.store.list(Library::Managed).unwrap().len(), 1);
        assert_eq!(again.meta.taken_at_ms, when, "filed under the file's time");
        // The second import is what the record now says.
        assert_eq!(
            f.store.get(&first.meta.id).unwrap().meta.description,
            "old save again"
        );
    }

    /// Two *different* saves landing on one id would be one destroying
    /// the other, so that case moves along instead of overwriting.
    #[test]
    fn a_different_save_never_overwrites_an_existing_record() {
        let f = fixture();
        let when = 1_700_000_000_000;
        let first = f
            .store
            .capture_at(&f.save, "first", SaveKind::Imported, when)
            .unwrap();

        // Same instant, different contents.
        write_save(&f.save, 999);
        let second = f
            .store
            .capture_at(&f.save, "second", SaveKind::Imported, when)
            .unwrap();

        assert_ne!(first.meta.id, second.meta.id);
        assert_eq!(f.store.list(Library::Managed).unwrap().len(), 2);
        assert_eq!(
            f.store.get(&first.meta.id).unwrap().meta.description,
            "first",
            "the original record survived"
        );
    }

    /// Archiving the live save is still stamped now, not with whenever
    /// the game last wrote the file: that copy is a bookmark the user
    /// made, and belongs at the moment they made it.
    #[test]
    fn a_manual_archive_is_filed_under_now() {
        let f = fixture();
        let before = now_ms();
        let stored = f.store.capture(&f.save, "x", SaveKind::Manual).unwrap();
        assert!(stored.meta.taken_at_ms >= before);
    }

    /// Importing has to be able to say *which* record already holds the
    /// bytes, so the warning can name it rather than just assert one
    /// exists.
    #[test]
    fn find_by_hash_names_the_record_holding_those_bytes() {
        let f = fixture();
        let stored = f
            .store
            .capture(&f.save, "the one", SaveKind::Manual)
            .unwrap();

        let found = f
            .store
            .find_by_hash(&stored.meta.sha256)
            .unwrap()
            .expect("the record that holds them");
        assert_eq!(found.id, stored.meta.id);
        assert_eq!(found.description, "the one");

        assert!(f.store.find_by_hash(&"0".repeat(64)).unwrap().is_none());
    }

    /// Prunes by id, which only the tests need.
    fn prune(store: &SaveStore, id: &str) {
        let record = store.get(id).expect("record exists");
        store.prune_record(record).expect("prunes");
    }

    /// Writes a save carrying a constellation, so pruning has something
    /// to lose.
    fn write_save_with_constellation(path: &Path, stars: usize) {
        write_save(path, 100);
        let mut save = ml2_save::SaveFile::read(path).unwrap();
        let chart = ml2_save::Constellation {
            stars: (0..stars)
                .map(|i| ml2_save::ConstellationStar {
                    kind: 0,
                    x: 0.1 * i as f32,
                    y: -0.2 * i as f32,
                    size: 0.9,
                    red: 1.0,
                    green: 1.0,
                    blue: 1.0,
                    alpha: 1.0,
                    halo_red: 0.12,
                    halo_green: 0.42,
                    halo_blue: 0.0,
                    halo_alpha: 1.0,
                    canis_ring: false,
                    fidelis_ring: false,
                    unknown: 0,
                })
                .collect(),
            lines: vec![ml2_save::ConstellationLine { from: 0, to: 1 }],
            scale: 3.5,
            line_red_intensity: 0.0,
        };
        save.set_constellation(&chart).unwrap();
        save.write(path).unwrap();
    }

    /// Pruning must never cost a constellation.
    ///
    /// A save holds exactly one, and finishing the Cosmic Ocean again
    /// overwrites it, so the only place an old chart survives is whatever
    /// was archived while it was current. If retention took the chart
    /// with the save file, a bounded archive would quietly destroy the
    /// gallery - which is the one thing in this feature that cannot be
    /// reconstructed from anywhere else.
    #[test]
    fn pruning_keeps_the_constellation() {
        let f = fixture();
        write_save_with_constellation(&f.save, 4);

        let stored = f
            .store
            .capture(&f.save, "co win", SaveKind::Automatic)
            .unwrap();
        let before = stored
            .summary
            .constellation
            .clone()
            .expect("captured a chart");
        assert_eq!(before.stars.len(), 4);

        prune(&f.store, &stored.meta.id);

        let after = f.store.get(&stored.meta.id).unwrap();
        assert!(!after.restorable, "the save file is gone");
        let kept = after
            .summary
            .constellation
            .clone()
            .expect("the chart outlived the save file");
        assert_eq!(kept, before, "pruning changed the chart");
        // The gallery groups by shape, so that is what has to survive.
        assert_eq!(kept.signature(), before.signature());
    }

    /// The same guarantee through the retention policy itself, which is
    /// the path a user actually reaches it by.
    #[test]
    fn retention_prunes_save_files_and_keeps_charts() {
        let f = fixture();
        write_save_with_constellation(&f.save, 3);
        for i in 0..4 {
            // Distinct contents, or `capture` dedupes them by hash.
            let mut save = ml2_save::SaveFile::read(&f.save).unwrap();
            save.set_plays(100 + i);
            save.write(&f.save).unwrap();
            f.store
                .capture(&f.save, "auto", SaveKind::Automatic)
                .unwrap();
        }

        // A policy that keeps almost nothing, so most get pruned.
        let settings = RetentionSettings {
            keep_all: false,
            policy: crate::saves::retention::RetentionPolicy {
                hourly: 1,
                daily: 0,
                weekly: 0,
                monthly: 0,
                yearly: 0,
            },
        };
        let pruned = f.store.apply_retention(&settings).unwrap();
        assert!(pruned > 0, "the policy should have pruned something");

        let all = f.store.list(Library::Snapshots).unwrap();
        assert_eq!(all.len(), 4, "records are never deleted, only their saves");
        for record in &all {
            assert!(
                record.summary.constellation.is_some(),
                "every record kept its chart, pruned or not"
            );
        }
        assert!(
            all.iter().any(|r| !r.restorable),
            "and some really did lose their save file"
        );
    }

    /// `StoredSave` flattens `StoredSaveMeta`, so a field named `summary`
    /// on both would serialize twice and leave the frontend reading
    /// whichever key happened to come last.
    #[test]
    fn a_pruned_record_serializes_exactly_one_summary() {
        let f = fixture();
        let stored = f.store.capture(&f.save, "x", SaveKind::Automatic).unwrap();
        prune(&f.store, &stored.meta.id);
        let pruned = f.store.get(&stored.meta.id).unwrap();
        assert!(pruned.meta.summary.is_some(), "prune should bake stats in");

        let json = serde_json::to_string(&pruned).unwrap();
        assert_eq!(json.matches("\"summary\":").count(), 1);
        assert_eq!(json.matches("\"prunedSummary\":").count(), 1);

        // And the one the frontend reads is the resolved one.
        let value: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(value["summary"]["plays"], 100);
        assert_eq!(value["restorable"], false);
    }

    #[test]
    fn hashes_are_stable_and_distinguish_content() {
        assert_eq!(hash_hex(b"abc"), hash_hex(b"abc"));
        assert_ne!(hash_hex(b"abc"), hash_hex(b"abd"));
        assert_eq!(hash_hex(b"abc").len(), 64);
    }
}
