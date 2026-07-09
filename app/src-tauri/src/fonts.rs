//! System font enumeration for the tracker font picker.

use std::collections::BTreeSet;

/// Returns the sorted, de-duplicated font family names installed on this
/// machine so the tracker font picker offers fonts that will actually render.
/// A hardcoded list showed families the system may not have (e.g. "Helvetica"
/// on Windows silently falls back to Arial, so the two looked identical).
#[tauri::command]
pub async fn list_system_fonts() -> Result<Vec<String>, String> {
    tauri::async_runtime::spawn_blocking(|| {
        let mut db = fontdb::Database::new();
        db.load_system_fonts();
        let mut families: BTreeSet<String> = BTreeSet::new();
        for face in db.faces() {
            if let Some((name, _)) = face.families.first() {
                let trimmed = name.trim();
                // Skip blanks and the icon/symbol pseudo-families that aren't
                // useful for reading tracker text.
                if !trimmed.is_empty() {
                    families.insert(trimmed.to_string());
                }
            }
        }
        families.into_iter().collect::<Vec<_>>()
    })
    .await
    .map_err(|e| format!("font enumeration failed: {e}"))
}
