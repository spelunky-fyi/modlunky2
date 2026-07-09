// Level Editor backend. Owns the atlas builder, pack picker, editor-window
// spawn, and save flow.

use std::path::PathBuf;

use base64::{Engine as _, engine::general_purpose::STANDARD};
use image::GenericImageView;
use ml2_levels::{
    ChanceValue, LevelChance, LevelChances, LevelFile, LevelSetting, LevelSettingValue,
    LevelSettings, LevelTemplate, LevelTemplates, MonsterChance, MonsterChances, Room,
    SECTION_COMMENT, TileCode, TileCodes, VALID_LEVEL_CHANCES, VALID_LEVEL_SETTINGS,
    VALID_MONSTER_CHANCES, VALID_TILE_CODES, usable_short_codes,
};
use ml2_sprites::{AtlasOptions, TileInput, build_atlas};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

#[derive(Debug, Clone, Copy, Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum EditorMode {
    Vanilla,
    Custom,
}

impl EditorMode {
    fn as_url_param(self) -> &'static str {
        match self {
            Self::Vanilla => "vanilla",
            Self::Custom => "custom",
        }
    }

    fn display(self) -> &'static str {
        match self {
            Self::Vanilla => "Vanilla",
            Self::Custom => "Custom",
        }
    }
}

fn packs_dir() -> Result<PathBuf, String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    Ok(install_dir.join("Mods").join("Packs"))
}

/// A named floor-tile biome the atlas builder can prioritize. Names
/// match `Data/Textures/floor_{name}.png` in the extracted assets, so
/// the filename -> biome mapping in the frontend feeds this straight
/// through.
const FLOOR_BIOMES: &[&str] = &[
    "cave", "jungle", "volcano", "olmec", "temple", "tidepool", "ice", "babylon", "sunken",
    "beehive", "gold", "duat", "eggplant", "surface",
];

const TILE_SIZE: u32 = 128;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EditorAtlasTile {
    pub name: String,
    pub x: u32,
    pub y: u32,
    pub w: u32,
    pub h: u32,
    /// Sprite's natural width in grid cells. `>1` means the tile draws
    /// wider than a single cell and should overflow at render time.
    pub nat_w_cells: u32,
    /// Sprite's natural height in grid cells. `>1` means the tile draws
    /// taller than a single cell and should overflow up from the anchor.
    pub nat_h_cells: u32,
    /// Cells to shift the sprite LEFT of its placement cell. Positive =
    /// sprite appears to the left of the anchor cell. Derived from the
    /// draw_mode table (see `anchor_for_tile`). Zero for tiles without
    /// an explicit mode: they draw with the placement cell at their
    /// top-left, extending down and to the right.
    pub anchor_x_cells: f32,
    /// Cells to shift the sprite UP from its placement cell. Positive =
    /// sprite appears above the anchor cell.
    pub anchor_y_cells: f32,
}

/// Per-tile `draw_mode` table mapping sprite names to the anchoring
/// recipe applied in `adjust_texture_xy`. Names not present render
/// top-left (mode 0). Kept in Rust rather than shipped as data so the
/// frontend just receives resolved offsets.
fn draw_mode_for(name: &str) -> u8 {
    match name {
        "anubis" | "alienqueen" | "olmecship" | "crown_statue" => 7,
        "olmec" => 15,
        "kingu" => 18,
        "coffin" | "dog_sign" | "bunkbed" | "telescope" | "empress_grave" | "empty_mech"
        | "lavamander" | "mummy" | "ghist_door" | "minister" | "storage_guy" | "totem_trap"
        | "lion_trap" | "yeti_queen" | "yeti_king" | "crabman" | "giant_fly" => 2,
        "palace_table" | "palace_chandelier" => 11,
        "moai_statue" => 9,
        "mother_statue" => 10,
        "lamassu" | "madametusk" => 2,
        "giant_frog" => 17,
        "door" | "starting_exit" | "eggplant_door" | "fountain_head" | "humphead" => 13,
        "door2" | "door_drop_held" | "palace_entrance" | "door2_secret" | "ghist_door2" => 6,
        "idol" | "idol_held" | "ankh" | "plasma_cannon" | "lockedchest" | "vlad" => 4,
        "shopkeeper_vat" => 12,
        "yama" => 14,
        "ammit" => 16,
        _ => 0,
    }
}

/// Resolves a numeric draw mode into cell-space anchor offsets.
/// Positive `x` shifts the sprite left of its placement cell, positive
/// `y` shifts it up. `w` and `h` are the sprite's natural cell footprint.
fn anchor_from_mode(mode: u8, w: f32, h: f32) -> (f32, f32) {
    // The upstream constants (25, 50, 75, 100) are pixels at a 50 px
    // per cell reference, so they divide by 50 to become cell-space
    // offsets.
    match mode {
        1 => (0.0, -h / 2.0),
        2 => (0.0, h / 2.0),
        3 => (w / 3.2, h / 2.0),
        4 => (-w / 2.0, 0.0),
        5 => (0.0, h / 2.0 + 1.0),
        6 => (0.5, 0.44),
        7 => (0.0, h / 2.0 + 0.5),
        8 => (0.0, h / 2.0 - 1.0),
        9 => (1.5, h / 2.0 + 1.0),
        10 => (0.0, h / 2.0 + 2.0),
        11 => (1.0, 0.0),
        12 => (0.0, 1.0),
        13 => (0.5, h / 2.0),
        14 => (2.0, h - 1.0),
        15 => (1.0, h / 2.0 + 1.0),
        16 => (0.5, 0.0),
        17 => (w / 3.2, h / 2.0 - 0.5),
        18 => (1.5, h / 2.0 - 1.5),
        _ => (0.0, 0.0),
    }
}

fn anchor_for_tile(name: &str, nat_w: u32, nat_h: u32) -> (f32, f32) {
    anchor_from_mode(draw_mode_for(name), nat_w as f32, nat_h as f32)
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct EditorAtlas {
    /// Data URL: `data:image/png;base64,...`
    pub png_data_url: String,
    pub width: u32,
    pub height: u32,
    pub tile_size: u32,
    pub tiles: Vec<EditorAtlasTile>,
}

fn textures_dir() -> Result<PathBuf, String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    Ok(install_dir
        .join("Mods")
        .join("Extracted")
        .join("Data")
        .join("Textures"))
}

/// Slice a biome floor sheet into `TILE_SIZE` chunks and pack them into a
/// texture atlas. Names are `{biome}_r{row}_c{col}` so the frontend can
/// pick tiles by grid position. This proof-of-concept bypasses the full
/// biome+theme override logic to get a real Spelunky asset atlas fast.
///
/// The work is CPU-bound (PNG decode, chunk crop, atlas pack, PNG encode
/// with max compression) so it runs on a blocking thread. Without the
/// spawn_blocking hop, the whole webview freezes for a few hundred ms
/// while the atlas is built.
#[tauri::command]
pub async fn build_editor_atlas(biome: String) -> Result<EditorAtlas, String> {
    // Cheap upfront checks stay on the async runtime.
    if !FLOOR_BIOMES.contains(&biome.as_str()) {
        return Err(format!("unknown biome: {biome}"));
    }
    let dir = textures_dir()?;
    let path = dir.join(format!("floor_{biome}.png"));
    if !path.exists() {
        return Err(format!(
            "missing sheet {}; run Extract Assets first",
            path.display()
        ));
    }

    tauri::async_runtime::spawn_blocking(move || build_editor_atlas_sync(biome, path))
        .await
        .map_err(|e| format!("atlas task panicked: {e}"))?
}

fn build_editor_atlas_sync(biome: String, path: PathBuf) -> Result<EditorAtlas, String> {
    let sheet = image::open(&path).map_err(|e| format!("open {}: {e}", path.display()))?;
    let (sw, sh) = sheet.dimensions();
    if sw % TILE_SIZE != 0 || sh % TILE_SIZE != 0 {
        return Err(format!(
            "sheet {} is {sw}x{sh}, not a multiple of {TILE_SIZE}",
            path.display()
        ));
    }
    let cols = sw / TILE_SIZE;
    let rows = sh / TILE_SIZE;

    let mut inputs = Vec::with_capacity((cols * rows) as usize);
    for row in 0..rows {
        for col in 0..cols {
            let sub = sheet
                .view(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                .to_image();
            inputs.push(TileInput {
                name: format!("{biome}_r{row}_c{col}"),
                image: sub,
            });
        }
    }

    let atlas =
        build_atlas(inputs, AtlasOptions::default()).map_err(|e| format!("build atlas: {e}"))?;

    let tiles = atlas
        .tiles
        .into_iter()
        .map(|(name, uv)| EditorAtlasTile {
            name,
            x: uv.x,
            y: uv.y,
            w: uv.w,
            h: uv.h,
            // Biome floor tiles are always 1x1 and don't have a
            // draw mode, so the anchor collapses to (0, 0).
            nat_w_cells: 1,
            nat_h_cells: 1,
            anchor_x_cells: 0.0,
            anchor_y_cells: 0.0,
        })
        .collect();

    let mut png_data_url = String::from("data:image/png;base64,");
    STANDARD.encode_string(&atlas.png, &mut png_data_url);

    Ok(EditorAtlas {
        png_data_url,
        width: atlas.width,
        height: atlas.height,
        tile_size: TILE_SIZE,
        tiles,
    })
}

// ---- Splash / launcher API (phase 7.2) --------------------------------------

/// Lists pack names under `Mods/Packs/`, sorted alphabetically. Skips
/// hidden folders. Returns the same set regardless of mode; a future
/// refinement can filter to packs that actually have editable content
/// for the requested mode (custom mode: has a `Data/Levels/*.lvl` that's
/// not in the vanilla extracts).
#[tauri::command]
pub fn list_level_packs(_mode: EditorMode) -> Result<Vec<String>, String> {
    let dir = packs_dir()?;
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut ids = Vec::new();
    for entry in std::fs::read_dir(&dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        if !entry.file_type().map(|t| t.is_dir()).unwrap_or(false) {
            continue;
        }
        if let Some(name) = entry.file_name().to_str()
            && !name.starts_with('.')
        {
            ids.push(name.to_string());
        }
    }
    ids.sort_by_key(|a| a.to_lowercase());
    Ok(ids)
}

/// Validates a pack name for use as a path segment and returns it
/// trimmed but otherwise UNCHANGED. Spaces and other legal filename
/// characters are preserved so lookups match the real folder on disk --
/// a pack folder named `My Pack` must be found as `My Pack`, not
/// `My_Pack`. Rejects anything that could escape the packs dir. Use this
/// everywhere an existing pack is referenced.
fn validate_pack_name(name: &str) -> Result<String, String> {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return Err("pack name is empty".into());
    }
    if trimmed.contains('/')
        || trimmed.contains('\\')
        || trimmed.contains("..")
        || trimmed.starts_with('.')
    {
        return Err(format!("invalid pack name: {trimmed:?}"));
    }
    Ok(trimmed.to_string())
}

/// Derives a folder name for a NEW pack from a user-typed name: validates
/// as `validate_pack_name`, then collapses spaces to underscores so the
/// freshly-created folder is path/shell friendly. Only used at creation
/// time; existing packs are looked up by their real name via
/// `validate_pack_name`, so this must NOT run on a name that already
/// names a folder on disk (it would rewrite the spaces and miss).
fn sanitize_pack_name(name: &str) -> Result<String, String> {
    Ok(validate_pack_name(name)?.replace(' ', "_"))
}

/// Embedded template for a fresh pack's `main.lua`. `<ModName>` is
/// substituted with the sanitized pack name on write.
const MAIN_LUA_TEMPLATE: &str = include_str!("templates/main.lua");

const LEVEL_CONFIGURATION_FILE_NAME: &str = "level_configuration.ls";

/// Creates a new pack under `Mods/Packs/<name>/Data/Levels/`. Returns the
/// sanitized folder name that ended up on disk. Rejects names that already
/// exist rather than silently reusing them.
///
/// For a Custom pack it also scaffolds a `main.lua` (Level-Sequence-ready) and
/// an empty `level_configuration.ls` so the pack is playable end-to-end as
/// soon as the user adds a .lvl. A Vanilla pack just overrides base-game .lvl
/// files in `Data/Levels/` and needs neither, so those are skipped.
#[tauri::command]
pub fn create_level_pack(name: String, mode: EditorMode) -> Result<String, String> {
    let dir = packs_dir()?;
    let sanitized = sanitize_pack_name(&name)?;
    let target = dir.join(&sanitized);
    if target.exists() {
        return Err(format!("pack {sanitized:?} already exists"));
    }
    let levels = target.join("Data").join("Levels");
    std::fs::create_dir_all(&levels).map_err(|e| format!("mkdir {}: {e}", levels.display()))?;

    if matches!(mode, EditorMode::Custom) {
        let main_lua = MAIN_LUA_TEMPLATE.replace("<ModName>", &sanitized);
        let main_lua_path = target.join("main.lua");
        std::fs::write(&main_lua_path, main_lua)
            .map_err(|e| format!("write {}: {e}", main_lua_path.display()))?;

        let config_path = levels.join(LEVEL_CONFIGURATION_FILE_NAME);
        let empty_config = serde_json::to_string_pretty(&LevelConfigurations::default())
            .map_err(|e| e.to_string())?;
        std::fs::write(&config_path, empty_config)
            .map_err(|e| format!("write {}: {e}", config_path.display()))?;
    }

    Ok(sanitized)
}

/// Maximum entries per editor-mode recents list. Anything past this drops
/// off the tail on the next push, matching how OS "recent files" menus
/// stay short enough to scan.
const MAX_RECENT_PACKS: usize = 5;

fn recents_key(mode: EditorMode) -> &'static str {
    match mode {
        EditorMode::Vanilla => crate::config::KEY_RECENT_VANILLA_PACKS,
        EditorMode::Custom => crate::config::KEY_RECENT_CUSTOM_PACKS,
    }
}

fn load_recents(mode: EditorMode) -> Vec<String> {
    let obj = crate::config::load_raw();
    obj.get(recents_key(mode))
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(String::from))
                .collect()
        })
        .unwrap_or_default()
}

fn save_recents(mode: EditorMode, entries: Vec<String>) -> Result<(), String> {
    let key = recents_key(mode);
    if entries.is_empty() {
        crate::config::apply_json_field(key, None)
    } else {
        let value = serde_json::to_value(&entries).map_err(|e| e.to_string())?;
        crate::config::apply_json_field(key, Some(value))
    }
}

/// Ordered list of packs the user has recently opened in `mode`, most
/// recent first, capped at `MAX_RECENT_PACKS`. Missing key returns an
/// empty list. Entries whose pack folders no longer exist on disk get
/// filtered out and the pruned list is persisted, so the splash UI never
/// shows dead entries and storage doesn't accumulate stale names.
#[tauri::command]
pub fn list_recent_packs(mode: EditorMode) -> Vec<String> {
    let current = load_recents(mode);
    let Ok(packs_dir) = packs_dir() else {
        return current;
    };
    let live: Vec<String> = current
        .iter()
        .filter(|p| packs_dir.join(p).is_dir())
        .cloned()
        .collect();
    if live.len() != current.len() {
        // Prune the persisted list too; ignore write errors so the caller
        // still gets the correct live list even if the config write blows
        // up for some reason.
        let _ = save_recents(mode, live.clone());
    }
    live
}

/// Bumps a pack to the head of `mode`'s recents list. Idempotent: pushing
/// a pack that's already in the list moves it to the front instead of
/// duplicating. Overflow past `MAX_RECENT_PACKS` drops the tail.
#[tauri::command]
pub fn push_recent_pack(mode: EditorMode, pack: String) -> Result<(), String> {
    let sanitized = validate_pack_name(&pack)?;
    let mut current = load_recents(mode);
    current.retain(|p| p != &sanitized);
    current.insert(0, sanitized);
    current.truncate(MAX_RECENT_PACKS);
    save_recents(mode, current)
}

/// Drops a pack from `mode`'s recents (right-click "Remove from recents").
/// Silently succeeds if the pack isn't in the list so the UI can call this
/// idempotently.
#[tauri::command]
pub fn remove_recent_pack(mode: EditorMode, pack: String) -> Result<(), String> {
    let mut current = load_recents(mode);
    let before = current.len();
    current.retain(|p| p != &pack);
    if current.len() == before {
        return Ok(());
    }
    save_recents(mode, current)
}

/// Spawns a new Tauri window for an editor session. The frontend reads
/// `window.__editorContext` (injected via `initialization_script`) to know
/// which pack + mode to render, and swaps to `<EditorWindow>` instead of
/// the main tab shell.
///
/// This has to be `async` in Tauri v2: `WebviewWindowBuilder::build()`
/// needs to send a message to the main runtime thread and await a reply.
/// A sync command runs on the async runtime and blocks that reply from
/// arriving, causing build() to hang indefinitely and the new window to
/// appear as a frozen white pane.
#[tauri::command]
pub async fn open_level_editor_window(
    app: AppHandle,
    pack: String,
    mode: EditorMode,
) -> Result<(), String> {
    let sanitized = validate_pack_name(&pack)?;

    // Verify the pack exists so the new window doesn't point at nothing.
    let dir = packs_dir()?;
    if !dir.join(&sanitized).exists() {
        return Err(format!("pack {sanitized:?} not found"));
    }

    // Window label must be unique across the app. Include mode so
    // vanilla and custom editors on the same pack can coexist. Tauri
    // restricts labels to `[A-Za-z0-9_/:-]`, so anything else becomes
    // `_` here. The pack name itself (with its original characters)
    // still travels to the frontend intact via the init script and
    // window title.
    let label_pack = sanitized
        .to_lowercase()
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || c == '-' || c == '_' {
                c
            } else {
                '_'
            }
        })
        .collect::<String>();
    let label = format!("editor-{}-{}", mode.as_url_param(), label_pack);
    if let Some(existing) = app.get_webview_window(&label) {
        // Already open: focus it instead of opening a second copy.
        let _ = existing.set_focus();
        return Ok(());
    }

    let title = format!("{} - {} Editor - Modlunky2", sanitized, mode.display());

    // Pass the editor context via an initialization script rather than URL
    // params. WebviewUrl::App treats its PathBuf as a *path segment*, which
    // URL-encodes `?`/`&`/`=` and produces a broken URL that the webview
    // can't load. The init script runs in the target window before any of
    // the app's JS, so App.tsx can read window.__editorContext synchronously.
    let context = format!(
        "window.__editorContext = {{ pack: {}, mode: {} }};",
        serde_json::to_string(&sanitized).map_err(|e| e.to_string())?,
        serde_json::to_string(mode.as_url_param()).map_err(|e| e.to_string())?,
    );

    // Root path lets Tauri fall back to whatever the dev/frontendDist server
    // considers the app's entry (same as the main window). Naming a specific
    // file caused loads to fail on Windows.
    let window = WebviewWindowBuilder::new(&app, &label, WebviewUrl::App("/".into()))
        .title(&title)
        .inner_size(1600.0, 1000.0)
        .min_inner_size(1280.0, 800.0)
        .resizable(true)
        .initialization_script(&context)
        .build()
        .map_err(|e| format!("open window: {e}"))?;
    if let Err(e) = crate::window_icon::apply_window_icon(&window) {
        tracing::warn!("failed to set crisp window icon on {label}: {e}");
    }

    Ok(())
}

/// Returns the cp1252 character pool a `.lvl` file can use as tile codes.
/// The frontend picks the first char that isn't already assigned when the
/// user adds a new tile to the palette. Comes from `ml2_levels`.
#[tauri::command]
pub fn list_short_codes() -> Vec<String> {
    usable_short_codes()
        .into_iter()
        .map(|c| c.to_string())
        .collect()
}

/// The list of well-known tile-code names the level format defines.
/// Used as the source for the add-tile combobox's autocomplete. Custom
/// names beyond this list are still accepted (validation is non-strict).
#[tauri::command]
pub fn list_valid_tile_codes() -> Vec<&'static str> {
    let mut out = VALID_TILE_CODES.to_vec();
    out.sort_by_key(|a| a.to_lowercase());
    out
}

/// Whitelist commands surface the well-known names ml2_levels defines so
/// the Rules panel can offer autocomplete for the add-row form. Custom
/// names beyond these lists are still allowed (non-strict validation), the
/// autocomplete just helps discovery.

#[tauri::command]
pub fn list_valid_level_settings() -> Vec<&'static str> {
    let mut out = VALID_LEVEL_SETTINGS.to_vec();
    out.sort();
    out
}

#[tauri::command]
pub fn list_valid_level_chances() -> Vec<&'static str> {
    let mut out = VALID_LEVEL_CHANCES.to_vec();
    out.sort();
    out
}

#[tauri::command]
pub fn list_valid_monster_chances() -> Vec<&'static str> {
    let mut out = VALID_MONSTER_CHANCES.to_vec();
    out.sort();
    out
}

/// Cosmic Ocean starfield backdrop, bundled with the app (users don't
/// get this via Extract Assets; it's a stylized overlay shipped as
/// `static/images/cosmos.png`). Returned as a base64 data URL so the
/// frontend can load it into a Pixi texture without a separate fetch
/// pipeline.
const COSMOS_BACKDROP_BYTES: &[u8] = include_bytes!("../resources/backdrops/cosmos.png");

#[tauri::command]
pub fn get_cosmic_backdrop() -> String {
    let mut out = String::from("data:image/png;base64,");
    STANDARD.encode_string(COSMOS_BACKDROP_BYTES, &mut out);
    out
}

/// Returns a 512x512 crop from `Data/Textures/deco_cosmic.png` for the
/// requested Cosmic Ocean subtheme. The frontend scatters this crop as
/// 31 rotated/scaled sprites over the cosmos.png starfield when the
/// background theme is set to Cosmic Ocean. Returns None if the user
/// hasn't extracted textures yet (the CO backdrop still tiles without
/// the subtheme decorations, so this is a graceful degrade rather than
/// an error).
#[tauri::command]
pub async fn get_cosmic_subtheme_decoration(subtheme_id: i32) -> Result<Option<String>, String> {
    let (row, col) = match subtheme_id {
        1 => (0, 0),           // Dwelling
        2 | 4 => (0, 1),       // Jungle / Olmec
        3 => (0, 2),           // Volcana
        5 | 13 | 14 => (0, 3), // Tide Pool / Abzu / Tiamat
        6 | 11 | 12 => (1, 0), // Temple / City of Gold / Duat
        7 => (1, 1),           // Ice Caves
        8 => (1, 2),           // Neo Babylon
        9 | 16 => (1, 3),      // Sunken City / Hundun
        _ => (0, 0),
    };
    let dir = textures_dir()?;
    let path = dir.join("deco_cosmic.png");
    if !path.exists() {
        return Ok(None);
    }
    tauri::async_runtime::spawn_blocking(move || -> Result<Option<String>, String> {
        const CHUNK: u32 = 512;
        let img = image::open(&path).map_err(|e| e.to_string())?;
        let crop = image::imageops::crop_imm(
            &img,
            (col as u32) * CHUNK,
            (row as u32) * CHUNK,
            CHUNK,
            CHUNK,
        )
        .to_image();
        let mut buf: Vec<u8> = Vec::new();
        {
            let mut cur = std::io::Cursor::new(&mut buf);
            image::DynamicImage::ImageRgba8(crop)
                .write_to(&mut cur, image::ImageFormat::Png)
                .map_err(|e| e.to_string())?;
        }
        let mut out = String::from("data:image/png;base64,");
        STANDARD.encode_string(&buf, &mut out);
        Ok(Some(out))
    })
    .await
    .map_err(|e| format!("deco crop task panicked: {e}"))?
}

/// Returns the biome-themed background PNG as a base64 data URL for the
/// canvas to use as a tiled backdrop behind the level tiles. Comes straight
/// from `Data/Textures/bg_{biome}.png` in the extracts.
#[tauri::command]
pub async fn get_biome_background(biome: String) -> Result<String, String> {
    if !FLOOR_BIOMES.contains(&biome.as_str()) {
        return Err(format!("unknown biome: {biome}"));
    }
    let dir = textures_dir()?;
    let path = dir.join(format!("bg_{biome}.png"));
    if !path.exists() {
        return Err(format!(
            "missing background {}; run Extract Assets first",
            path.display()
        ));
    }
    tauri::async_runtime::spawn_blocking(move || -> Result<String, String> {
        let bytes = std::fs::read(&path).map_err(|e| e.to_string())?;
        let mut out = String::from("data:image/png;base64,");
        STANDARD.encode_string(&bytes, &mut out);
        Ok(out)
    })
    .await
    .map_err(|e| format!("bg task panicked: {e}"))?
}

// ---- Custom level loading + procedural atlas (phase 7.3 spike) --------------

const ROOM_TILE_W: u32 = 10;
const ROOM_TILE_H: u32 = 8;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CustomLevelPaletteEntry {
    pub name: String,
    /// The single-character tile code as it appears in the file. May be a
    /// non-ASCII cp1252 byte (e.g. `€`, `ç`), which is why it's a String.
    pub code: String,
    pub comment: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct CustomLevelData {
    pub file_name: String,
    pub width_rooms: u32,
    pub height_rooms: u32,
    pub width_tiles: u32,
    pub height_tiles: u32,
    /// Row-major grid of tile-code names, height_tiles rows by width_tiles
    /// cols. Empty string for cells not covered by any setroom template.
    pub foreground: Vec<Vec<String>>,
    /// Same shape as `foreground`. Cells not covered by a dual setroom
    /// template come back as empty strings, so the editor can distinguish
    /// "author never touched the back layer here" from an author-placed
    /// blank cell.
    pub background: Vec<Vec<String>>,
    pub palette: Vec<CustomLevelPaletteEntry>,
    /// The save format the file was recognised as, if any of the known
    /// formats matched a template. `None` means load couldn't identify
    /// the format; the frontend then triggers the recovery flow.
    pub detected_format: Option<CustomLevelSaveFormat>,
    /// Best-guess template pattern derived from the file's actual
    /// template names via regex. Populated whenever a template shaped
    /// like `<prefix><digits><sep><digits><suffix>` exists in the file;
    /// used to prefill the "define a format" recovery dialog.
    pub suggested_format: Option<String>,
    /// Theme id inferred from the (0,0) setroom template's comment
    /// (biome name string). Populated when the comment resolves via
    /// `theme_id_for_biome_name`. Frontend uses this as the default
    /// when the file has no `level_configuration.ls` entry.
    pub detected_theme: Option<i32>,
}

// --- LevelSequence Lua library install --------------------------------------

const LEVEL_SEQUENCE_REPO: &str = "jaythebusinessgoose/LevelSequence";
const LEVEL_SEQUENCE_ASSET_NAME: &str = "LevelSequence.zip";
/// GitHub API endpoint for the library's latest release. Rate-limited to
/// 60 unauthed requests per hour per IP; no client-side cache, this
/// relies on the "check for updates" affordance not being spammed.
fn level_sequence_latest_api_url() -> String {
    format!("https://api.github.com/repos/{LEVEL_SEQUENCE_REPO}/releases/latest")
}

/// State of the LevelSequence Lua library inside a specific pack. The
/// splash / editor UI drives its Install / Update / Reinstall label from
/// (folder_exists, installed_version, latest_version).
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LevelSequenceStatus {
    /// True if `<pack>/LevelSequence/` exists on disk. False means the
    /// library isn't installed at all.
    pub folder_exists: bool,
    /// Version tag last installed (e.g. "v3.0"), read from the
    /// `current.json` marker written on install. `None` when the folder
    /// exists but no marker is present (installed via git / manually);
    /// the UI surfaces this as a "managed externally" note.
    pub installed_version: Option<String>,
}

fn level_sequence_dir(pack: &str) -> Result<PathBuf, String> {
    let sanitized = validate_pack_name(pack)?;
    Ok(packs_dir()?.join(&sanitized).join("LevelSequence"))
}

fn read_installed_version(dir: &std::path::Path) -> Option<String> {
    let marker = dir.join("current.json");
    let raw = std::fs::read_to_string(marker).ok()?;
    let value: serde_json::Value = serde_json::from_str(&raw).ok()?;
    value.get("version")?.as_str().map(String::from)
}

/// Returns the current state of the pack's LevelSequence library:
/// folder present, and (if this app installed it) which version.
#[tauri::command]
pub fn get_level_sequence_status(pack: String) -> Result<LevelSequenceStatus, String> {
    let dir = level_sequence_dir(&pack)?;
    let folder_exists = dir.is_dir();
    let installed_version = if folder_exists {
        read_installed_version(&dir)
    } else {
        None
    };
    Ok(LevelSequenceStatus {
        folder_exists,
        installed_version,
    })
}

/// Fetches the latest published tag from the LevelSequence GitHub repo.
/// Returns just the tag string (e.g. "v3.0"); callers compare it against
/// the installed version to decide whether an update is available.
#[tauri::command]
pub async fn check_latest_level_sequence() -> Result<String, String> {
    let client = reqwest::Client::builder()
        .user_agent("modlunky2-tauri")
        .connect_timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| format!("http client: {e}"))?;
    let resp = client
        .get(level_sequence_latest_api_url())
        .header("Accept", "application/vnd.github+json")
        .send()
        .await
        .map_err(|e| format!("fetch latest: {e}"))?;
    if !resp.status().is_success() {
        return Err(format!("github responded {}", resp.status()));
    }
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("parse release json: {e}"))?;
    body.get("tag_name")
        .and_then(|v| v.as_str())
        .map(String::from)
        .ok_or_else(|| "release json missing tag_name".to_string())
}

/// Downloads the latest LevelSequence.zip and extracts it into
/// `<pack>/LevelSequence/`. Wipes any existing install so a corrupted
/// partial state can't linger. Writes `current.json` with the tag so
/// subsequent status checks report the version just landed. Returns
/// the installed tag on success.
#[tauri::command]
pub async fn install_level_sequence(pack: String) -> Result<String, String> {
    use std::io::Cursor;
    let dir = level_sequence_dir(&pack)?;

    let client = reqwest::Client::builder()
        .user_agent("modlunky2-tauri")
        .connect_timeout(std::time::Duration::from_secs(10))
        .build()
        .map_err(|e| format!("http client: {e}"))?;

    // Resolve latest first so the target tag is known. Doing this in
    // the same call means the write-current.json step below can stamp
    // the exact version just downloaded.
    let latest_resp = client
        .get(level_sequence_latest_api_url())
        .header("Accept", "application/vnd.github+json")
        .send()
        .await
        .map_err(|e| format!("fetch latest: {e}"))?;
    if !latest_resp.status().is_success() {
        return Err(format!("github responded {}", latest_resp.status()));
    }
    let body: serde_json::Value = latest_resp
        .json()
        .await
        .map_err(|e| format!("parse release json: {e}"))?;
    let tag = body
        .get("tag_name")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "release json missing tag_name".to_string())?
        .to_string();
    // Compose the asset URL from the tag. GitHub keeps a stable
    // `/releases/download/<tag>/<asset>` path, so walking the assets
    // array again isn't needed.
    let download_url = format!(
        "https://github.com/{LEVEL_SEQUENCE_REPO}/releases/download/{tag}/{LEVEL_SEQUENCE_ASSET_NAME}"
    );

    let zip_resp = client
        .get(&download_url)
        .send()
        .await
        .map_err(|e| format!("download {download_url}: {e}"))?;
    if !zip_resp.status().is_success() {
        return Err(format!("download responded {}", zip_resp.status()));
    }
    let mut buf: Vec<u8> = Vec::new();
    let mut stream = zip_resp.bytes_stream();
    use futures_util::StreamExt;
    while let Some(chunk) = stream.next().await {
        let bytes = chunk.map_err(|e| format!("read stream: {e}"))?;
        buf.extend_from_slice(&bytes);
    }

    let dir_clone = dir.clone();
    let tag_clone = tag.clone();
    tauri::async_runtime::spawn_blocking(move || -> Result<(), String> {
        // Nuke and repave so an aborted previous install doesn't leave
        // orphan files that the new zip doesn't cover.
        if dir_clone.exists() {
            std::fs::remove_dir_all(&dir_clone)
                .map_err(|e| format!("wipe {}: {e}", dir_clone.display()))?;
        }
        std::fs::create_dir_all(&dir_clone)
            .map_err(|e| format!("mkdir {}: {e}", dir_clone.display()))?;

        let mut archive =
            zip::ZipArchive::new(Cursor::new(buf)).map_err(|e| format!("open zip: {e}"))?;
        for i in 0..archive.len() {
            let mut file = archive
                .by_index(i)
                .map_err(|e| format!("read entry {i}: {e}"))?;
            let Some(name) = file.enclosed_name() else {
                continue;
            };
            let dest = dir_clone.join(&name);
            if file.is_dir() {
                std::fs::create_dir_all(&dest)
                    .map_err(|e| format!("mkdir {}: {e}", dest.display()))?;
                continue;
            }
            if let Some(parent) = dest.parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
            }
            let mut out = std::fs::File::create(&dest)
                .map_err(|e| format!("create {}: {e}", dest.display()))?;
            std::io::copy(&mut file, &mut out)
                .map_err(|e| format!("write {}: {e}", dest.display()))?;
        }

        // Stamp the version so status checks report what just landed
        // rather than requiring another GitHub round-trip.
        let marker = dir_clone.join("current.json");
        let payload = serde_json::json!({ "version": tag_clone });
        std::fs::write(&marker, payload.to_string())
            .map_err(|e| format!("write {}: {e}", marker.display()))?;
        Ok(())
    })
    .await
    .map_err(|e| format!("install task panicked: {e}"))??;
    Ok(tag)
}

// --- Custom save formats ----------------------------------------------------

/// Setroom template naming scheme for a custom level. Field names use
/// snake_case for on-disk stability.
#[derive(Debug, Clone, Default, Deserialize, Serialize, PartialEq)]
pub struct CustomLevelSaveFormat {
    /// Human-readable label. Also serves as the identity key for remove /
    /// default-select operations; no two saved formats may share a name.
    pub name: String,
    /// Template pattern containing exactly one `{y}` and one `{x}`. Fed to
    /// `format_setroom_name` on save; regexed against actual template
    /// names on load to detect which format a file uses.
    pub room_template_format: String,
    /// Whether to auto-emit dash-format vanilla setroom mirrors on the
    /// boss / special themes. Off for authoring vanilla-native packs.
    pub include_vanilla_setrooms: bool,
}

fn validate_save_format(fmt: &CustomLevelSaveFormat) -> Result<(), String> {
    let trimmed = fmt.name.trim();
    if trimmed.is_empty() {
        return Err("save format name is empty".into());
    }
    // Reserve the built-in names so users can't shadow / redefine them.
    if trimmed.eq_ignore_ascii_case("LevelSequence")
        || trimmed.eq_ignore_ascii_case("Vanilla setroom [warning]")
    {
        return Err(format!(
            "save format name {trimmed:?} is reserved for a built-in"
        ));
    }
    validate_room_template_format(&fmt.room_template_format)?;
    // Reject templates that collide with a built-in pattern; users who want
    // that behavior should just pick the built-in.
    let pat = fmt.room_template_format.as_str();
    if pat == "setroom{y}_{x}" || pat == "setroom{y}-{x}" {
        return Err(format!(
            "save format {pat:?} matches a built-in; use the built-in instead"
        ));
    }
    Ok(())
}

fn load_custom_save_formats_raw() -> Vec<CustomLevelSaveFormat> {
    let obj = crate::config::load_raw();
    obj.get(crate::config::KEY_CUSTOM_SAVE_FORMATS)
        .and_then(|v| serde_json::from_value::<Vec<CustomLevelSaveFormat>>(v.clone()).ok())
        .unwrap_or_default()
}

/// Returns the user-authored setroom formats from the shared config.json.
/// Built-ins live on the frontend, since they're static; only user-defined
/// formats need round-tripping.
#[tauri::command]
pub fn list_custom_save_formats() -> Vec<CustomLevelSaveFormat> {
    load_custom_save_formats_raw()
}

/// Appends a user-defined format to the config. Rejects duplicates by
/// name so remove-by-name stays unambiguous later.
#[tauri::command]
pub fn add_custom_save_format(format: CustomLevelSaveFormat) -> Result<(), String> {
    validate_save_format(&format)?;
    let mut current = load_custom_save_formats_raw();
    if current.iter().any(|f| f.name == format.name) {
        return Err(format!("save format {:?} already exists", format.name));
    }
    current.push(format);
    let value = serde_json::to_value(&current).map_err(|e| e.to_string())?;
    crate::config::apply_json_field(crate::config::KEY_CUSTOM_SAVE_FORMATS, Some(value))
}

/// Removes a user-defined format by name. Silently succeeds if no format
/// with that name exists so the UI can call this idempotently.
#[tauri::command]
pub fn remove_custom_save_format(name: String) -> Result<(), String> {
    let mut current = load_custom_save_formats_raw();
    let before = current.len();
    current.retain(|f| f.name != name);
    if current.len() == before {
        return Ok(());
    }
    if current.is_empty() {
        crate::config::apply_json_field(crate::config::KEY_CUSTOM_SAVE_FORMATS, None)
    } else {
        let value = serde_json::to_value(&current).map_err(|e| e.to_string())?;
        crate::config::apply_json_field(crate::config::KEY_CUSTOM_SAVE_FORMATS, Some(value))
    }
}

/// Returns the format the editor uses by default for new levels and as the
/// preferred detection hint on load. `None` means "no default set" and
/// the frontend falls back to its LevelSequence built-in.
#[tauri::command]
pub fn get_default_save_format() -> Option<CustomLevelSaveFormat> {
    let obj = crate::config::load_raw();
    obj.get(crate::config::KEY_DEFAULT_SAVE_FORMAT)
        .and_then(|v| serde_json::from_value::<CustomLevelSaveFormat>(v.clone()).ok())
}

/// Persists (or clears when `format` is `None`) the pack-wide default
/// save format. Value validation matches `add_custom_save_format` for
/// user-defined formats; built-ins pass through unchecked (they're
/// trusted names owned by the frontend).
#[tauri::command]
pub fn set_default_save_format(format: Option<CustomLevelSaveFormat>) -> Result<(), String> {
    match format {
        Some(f) => {
            // Built-ins land here too, and they have reserved names +
            // built-in patterns validate_save_format rejects. Skip
            // validation for names the frontend marks as built-in by
            // passing the exact known strings.
            let is_builtin = f.name == "LevelSequence" || f.name == "Vanilla setroom [warning]";
            if !is_builtin {
                validate_save_format(&f)?;
            }
            let value = serde_json::to_value(&f).map_err(|e| e.to_string())?;
            crate::config::apply_json_field(crate::config::KEY_DEFAULT_SAVE_FORMAT, Some(value))
        }
        None => crate::config::apply_json_field(crate::config::KEY_DEFAULT_SAVE_FORMAT, None),
    }
}

/// App-wide level-editor UI preferences shared by both editors and the splash
/// settings. Persisted as one JSON object under `KEY_EDITOR_PREFS`. Missing
/// fields fall back to `Default` (container `#[serde(default)]`) so older /
/// partial configs still load.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", default)]
pub struct EditorPrefs {
    /// How the canvas zooms when a room first renders: "fit" (fit-to-view,
    /// the historical behavior), "fixed" (always `fixed_zoom_pct`), or
    /// "remember" (100% first, then carry the last zoom as you navigate).
    pub zoom_mode: String,
    /// Zoom level (percent) used when `zoom_mode` is "fixed". Clamped to the
    /// canvas's 25..=800 range on the frontend.
    pub fixed_zoom_pct: u32,
    /// "Clamp" render toggle: draw every sprite inside its placement cell
    /// instead of at natural size.
    pub clamp_render: bool,
    /// Default visibility of the fine (per-tile) grid overlay.
    pub show_tile_grid: bool,
    /// Default visibility of the room-boundary grid overlay.
    pub show_room_grid: bool,
    /// Collapse the palette to icon-only swatches that wrap into a dense grid.
    /// Shared across both editors; reorder mode ignores it and stays expanded.
    pub palette_dense: bool,
}

impl Default for EditorPrefs {
    fn default() -> Self {
        Self {
            zoom_mode: "fit".to_string(),
            fixed_zoom_pct: 100,
            clamp_render: false,
            show_tile_grid: true,
            show_room_grid: true,
            palette_dense: false,
        }
    }
}

/// Returns the persisted editor preferences, or defaults when unset.
#[tauri::command]
pub fn get_editor_prefs() -> EditorPrefs {
    crate::config::load_raw()
        .get(crate::config::KEY_EDITOR_PREFS)
        .and_then(|v| serde_json::from_value::<EditorPrefs>(v.clone()).ok())
        .unwrap_or_default()
}

/// Persists the full editor preferences object.
#[tauri::command]
pub fn set_editor_prefs(prefs: EditorPrefs) -> Result<(), String> {
    let value = serde_json::to_value(&prefs).map_err(|e| e.to_string())?;
    crate::config::apply_json_field(crate::config::KEY_EDITOR_PREFS, Some(value))
}

// --- level_configuration.ls -------------------------------------------------

/// One level's playthrough configuration. Field names use snake_case
/// to match the on-disk JSON format.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct LevelConfiguration {
    pub identifier: String,
    pub name: String,
    pub file_name: String,
    pub theme: i32,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subtheme: Option<i32>,
    /// Only meaningful for Cosmic Ocean levels.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub width: Option<i32>,
    /// Only meaningful for Cosmic Ocean levels.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub height: Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub border_theme: Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    #[serde(rename = "loop")]
    pub loop_: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dont_loop: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub border_entity_theme: Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub floor_theme: Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub background_theme: Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub background_texture_theme: Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub music_theme: Option<i32>,
    #[serde(default, skip_serializing_if = "is_false")]
    pub skip_co_fixes: bool,
    #[serde(default, skip_serializing_if = "is_false")]
    pub spawn_door_jellyfish: bool,
}

fn is_false(v: &bool) -> bool {
    !*v
}

/// Pack-wide level playthrough config. `sequence` is the ordered
/// playthrough; `all_configurations` is an out-of-band map of "known"
/// levels (e.g. warp targets) keyed by their identifier.
/// Deserialization is lenient: a missing file yields the default empty
/// struct, and a malformed file also yields the default so a stray
/// parse error doesn't block the UI.
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
pub struct LevelConfigurations {
    #[serde(default)]
    pub sequence: Vec<LevelConfiguration>,
    #[serde(default, skip_serializing_if = "std::collections::BTreeMap::is_empty")]
    pub all_configurations: std::collections::BTreeMap<String, LevelConfiguration>,
}

fn resolve_pack_level_path(pack: &str, file_name: &str) -> Result<PathBuf, String> {
    let sanitized = validate_pack_name(pack)?;
    if file_name.contains("..") || file_name.starts_with('/') || file_name.starts_with('\\') {
        return Err(format!("invalid level file: {file_name:?}"));
    }
    Ok(packs_dir()?
        .join(&sanitized)
        .join("Data")
        .join("Levels")
        .join(file_name))
}

/// Lists `.lvl` files under the pack's `Data/Levels/`, including any
/// `Arena/*.lvl`. Filenames are relative to `Data/Levels/`. Doesn't
/// filter against extracts; showing everything a pack ships is more
/// useful for the current editor UX.
#[tauri::command]
pub fn list_custom_levels(pack: String) -> Result<Vec<String>, String> {
    let sanitized = validate_pack_name(&pack)?;
    let dir = packs_dir()?.join(&sanitized).join("Data").join("Levels");
    if !dir.exists() {
        return Ok(Vec::new());
    }
    let mut out = Vec::new();
    let entries = std::fs::read_dir(&dir).map_err(|e| e.to_string())?;
    for entry in entries {
        let entry = entry.map_err(|e| e.to_string())?;
        let ft = entry.file_type().map_err(|e| e.to_string())?;
        let file_name_os = entry.file_name();
        let Some(name) = file_name_os.to_str() else {
            continue;
        };
        if ft.is_file() && name.to_lowercase().ends_with(".lvl") {
            out.push(name.to_string());
        } else if ft.is_dir() && name.eq_ignore_ascii_case("Arena") {
            let arena_entries = std::fs::read_dir(entry.path()).map_err(|e| e.to_string())?;
            for ae in arena_entries {
                let ae = ae.map_err(|e| e.to_string())?;
                if !ae.file_type().map(|t| t.is_file()).unwrap_or(false) {
                    continue;
                }
                if let Some(n) = ae.file_name().to_str()
                    && n.to_lowercase().ends_with(".lvl")
                {
                    out.push(format!("Arena/{n}"));
                }
            }
        }
    }
    out.sort_by_key(|a| a.to_lowercase());
    Ok(out)
}

fn resolve_level_config_path(pack: &str) -> Result<PathBuf, String> {
    let sanitized = validate_pack_name(pack)?;
    Ok(packs_dir()?
        .join(&sanitized)
        .join("Data")
        .join("Levels")
        .join(LEVEL_CONFIGURATION_FILE_NAME))
}

/// Reads the pack's `level_configuration.ls`. A missing file returns
/// the default empty struct so brand-new packs and the Sequence panel
/// don't have to special-case first-time-open. A malformed file
/// returns the default too, so a stray parse error doesn't block the
/// UI.
#[tauri::command]
pub fn load_custom_config(pack: String) -> Result<LevelConfigurations, String> {
    let path = resolve_level_config_path(&pack)?;
    if !path.exists() {
        return Ok(LevelConfigurations::default());
    }
    let raw =
        std::fs::read_to_string(&path).map_err(|e| format!("read {}: {e}", path.display()))?;
    Ok(serde_json::from_str::<LevelConfigurations>(&raw).unwrap_or_default())
}

/// Writes the pack's `level_configuration.ls`. Uses a `.tmp` sibling + rename
/// so a partial write can't corrupt the previous file. Creates the parent
/// `Data/Levels/` directory if it's somehow missing (belt + suspenders with
/// `create_level_pack`).
#[tauri::command]
pub fn save_custom_config(pack: String, config: LevelConfigurations) -> Result<(), String> {
    let path = resolve_level_config_path(&pack)?;
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
    }
    let body = serde_json::to_string_pretty(&config).map_err(|e| e.to_string())?;
    let tmp = path.with_extension("ls.tmp");
    std::fs::write(&tmp, body).map_err(|e| format!("write {}: {e}", tmp.display()))?;
    std::fs::rename(&tmp, &path).map_err(|e| format!("rename {}: {e}", path.display()))?;
    Ok(())
}

/// Parses `setroom{y}_{x}` (LevelSequence) or `setroom{y}-{x}` (vanilla) into
/// `(x, y)`. Room 0-0 is the top-left cell.
fn parse_setroom_name(name: &str) -> Option<(u32, u32)> {
    let rest = name.strip_prefix("setroom")?;
    let (y_str, x_str) = rest.split_once('_').or_else(|| rest.split_once('-'))?;
    Some((x_str.parse().ok()?, y_str.parse().ok()?))
}

/// Extract `(x, y)` from a template name using an arbitrary format
/// pattern with `{y}` and `{x}` placeholders. Returns `None` when the
/// name doesn't fit the pattern shape, when either digit-run is missing,
/// or when the pattern's middle segment is empty (which would make the
/// split between `{y}` and `{x}` ambiguous).
fn match_template_pattern(pattern: &str, name: &str) -> Option<(u32, u32)> {
    let y_idx = pattern.find("{y}")?;
    let x_idx = pattern.find("{x}")?;
    if y_idx == x_idx {
        return None;
    }
    let y_first = y_idx < x_idx;
    let (first_ph, second_ph) = if y_first {
        ("{y}", "{x}")
    } else {
        ("{x}", "{y}")
    };
    let (prefix, rest) = pattern.split_once(first_ph)?;
    let (middle, suffix) = rest.split_once(second_ph)?;
    if middle.is_empty() {
        return None;
    }
    let stripped = name.strip_prefix(prefix)?.strip_suffix(suffix)?;
    let mid_pos = stripped.find(middle)?;
    let first_str = &stripped[..mid_pos];
    let second_str = &stripped[mid_pos + middle.len()..];
    let first: u32 = first_str.parse().ok()?;
    let second: u32 = second_str.parse().ok()?;
    Some(if y_first {
        (second, first)
    } else {
        (first, second)
    })
}

/// Best-guess template pattern derived from an existing template name,
/// so the recovery dialog can pre-fill something useful. Split the name
/// on the first two digit runs and substitute `{y}` and `{x}` in
/// place. Returns `None` when the name doesn't have two digit runs to
/// work with.
fn suggest_format_from_name(name: &str) -> Option<String> {
    let bytes: Vec<char> = name.chars().collect();
    let mut i = 0;
    while i < bytes.len() && !bytes[i].is_ascii_digit() {
        i += 1;
    }
    let begin_end = i;
    if i == bytes.len() {
        return None;
    }
    while i < bytes.len() && bytes[i].is_ascii_digit() {
        i += 1;
    }
    let mid_start = i;
    while i < bytes.len() && !bytes[i].is_ascii_digit() {
        i += 1;
    }
    let mid_end = i;
    if i == bytes.len() {
        return None;
    }
    while i < bytes.len() && bytes[i].is_ascii_digit() {
        i += 1;
    }
    let end_start = i;
    let begin: String = bytes[..begin_end].iter().collect();
    let middle: String = bytes[mid_start..mid_end].iter().collect();
    let end: String = bytes[end_start..].iter().collect();
    Some(format!("{begin}{{y}}{middle}{{x}}{end}"))
}

/// Loads a custom level's .lvl file and returns it as a flat W×H grid of
/// tile-code NAMES (not chars). Reads the `size` LevelSetting for the
/// room dimensions and inlays each recognised setroom template's first
/// room at `(x*10, y*8)`. Cells not covered by any template stay as empty
/// strings.
///
/// `known_formats` is the caller's ordered list of formats to try when
/// detecting which naming scheme the file uses. Earlier entries win, so
/// the frontend should sort a pack's default first, then user-defined
/// formats, then built-ins. If nothing matches, load falls back to the
/// legacy underscore-vs-dash setroom parser and reports `detected_format
/// = None`, letting the frontend pop the recovery dialog.
#[tauri::command]
pub async fn load_custom_level(
    pack: String,
    file_name: String,
    known_formats: Vec<CustomLevelSaveFormat>,
) -> Result<CustomLevelData, String> {
    let path = resolve_pack_level_path(&pack, &file_name)?;
    if !path.exists() {
        return Err(format!("level not found: {}", path.display()));
    }
    tauri::async_runtime::spawn_blocking(move || {
        load_custom_level_sync(file_name, path, known_formats)
    })
    .await
    .map_err(|e| format!("load task panicked: {e}"))?
}

fn load_custom_level_sync(
    file_name: String,
    path: PathBuf,
    known_formats: Vec<CustomLevelSaveFormat>,
) -> Result<CustomLevelData, String> {
    let level = LevelFile::from_path(&path).map_err(|e| e.to_string())?;

    // Room dimensions come from the \-size setting. Fall back to a
    // reasonable default so a size-less file still opens.
    let (width_rooms, height_rooms) = level
        .level_settings
        .get("size")
        .and_then(|s| match &s.value {
            ml2_levels::LevelSettingValue::Size(w, h) => {
                let w = w.parse::<u32>().ok()?;
                let h = h.parse::<u32>().ok()?;
                Some((w, h))
            }
            _ => None,
        })
        .unwrap_or((4, 4));

    let width_tiles = width_rooms * ROOM_TILE_W;
    let height_tiles = height_rooms * ROOM_TILE_H;

    // Build char -> name lookup from the tile-code table.
    let mut code_to_name: std::collections::HashMap<char, String> =
        std::collections::HashMap::new();
    let mut palette = Vec::new();
    for tc in level.tile_codes.all() {
        if let Some(ch) = tc.value.chars().next() {
            code_to_name.insert(ch, tc.name.clone());
        }
        palette.push(CustomLevelPaletteEntry {
            name: tc.name.clone(),
            code: tc.value.clone(),
            comment: tc.comment.clone(),
        });
    }

    // Format detection: the first known format that recognises any of
    // the file's templates wins. Templates that don't match the winning
    // format are ignored.
    let detected_format = known_formats.iter().find(|fmt| {
        level
            .level_templates
            .all()
            .any(|tpl| match_template_pattern(&fmt.room_template_format, &tpl.name).is_some())
    });

    let mut foreground: Vec<Vec<String>> =
        vec![vec![String::new(); width_tiles as usize]; height_tiles as usize];
    let mut background: Vec<Vec<String>> =
        vec![vec![String::new(); width_tiles as usize]; height_tiles as usize];
    let mut placed: std::collections::HashSet<(u32, u32)> = std::collections::HashSet::new();

    if let Some(fmt) = detected_format {
        // Single pass under the detected pattern. Non-matching templates
        // (e.g. auto-emitted dash-format mirrors from a LevelSequence
        // save) get ignored here; the winning format's templates are the
        // source of truth for the editor's grid state.
        for tpl in level.level_templates.all() {
            let Some((x, y)) = match_template_pattern(&fmt.room_template_format, &tpl.name) else {
                continue;
            };
            place_template(
                &mut foreground,
                &mut background,
                tpl,
                x,
                y,
                &code_to_name,
                &mut placed,
                width_rooms,
                height_rooms,
            );
        }
    } else {
        // Legacy path for files that don't fit any known format. Prefer
        // LevelSequence-style names (`setroomY_X`) over vanilla (`setroomY-X`)
        // when both are present at the same coord; walk in insertion order
        // and let underscore-first pass claim coords.
        for tpl in level.level_templates.all() {
            if !tpl.name.contains('_') {
                continue;
            }
            let Some((x, y)) = parse_setroom_name(&tpl.name) else {
                continue;
            };
            place_template(
                &mut foreground,
                &mut background,
                tpl,
                x,
                y,
                &code_to_name,
                &mut placed,
                width_rooms,
                height_rooms,
            );
        }
        for tpl in level.level_templates.all() {
            if !tpl.name.contains('-') {
                continue;
            }
            let Some((x, y)) = parse_setroom_name(&tpl.name) else {
                continue;
            };
            place_template(
                &mut foreground,
                &mut background,
                tpl,
                x,
                y,
                &code_to_name,
                &mut placed,
                width_rooms,
                height_rooms,
            );
        }
    }

    // Suggested pattern for the recovery dialog: derive from any template
    // name shaped like `<prefix><digits><middle><digits><suffix>`. First
    // hit wins so the user gets a concrete starting point.
    let suggested_format = if detected_format.is_some() {
        None
    } else {
        level
            .level_templates
            .all()
            .find_map(|tpl| suggest_format_from_name(&tpl.name))
    };

    // Read the (0,0) setroom template's comment to recover theme when
    // the file has no `level_configuration.ls` entry.
    let detected_theme = detected_format.and_then(|fmt| {
        let target = format_setroom_name(&fmt.room_template_format, 0, 0);
        level
            .level_templates
            .all()
            .find(|tpl| tpl.name == target)
            .and_then(|tpl| tpl.comment.as_deref())
            .and_then(theme_id_for_biome_name)
    });

    Ok(CustomLevelData {
        file_name,
        width_rooms,
        height_rooms,
        width_tiles,
        height_tiles,
        foreground,
        background,
        palette,
        detected_format: detected_format.cloned(),
        suggested_format,
        detected_theme,
    })
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SavePaletteEntry {
    pub name: String,
    pub code: String,
    pub comment: Option<String>,
}

/// Saves the edited grid + palette back to the pack's .lvl file.
/// Preserves everything not currently exposed in the UI (level settings,
/// chances, monsters, section comments) by reloading the file and only
/// overwriting the pieces that changed. Backs up the previous file to
/// `Mods/Backups/<pack>/` before writing.
///
/// `theme` is the LevelConfiguration.theme for the file. None means "not
/// in the pack's level_configuration.ls yet"; that skips the special-theme
/// vanilla-setroom mirror emission entirely.
///
/// `save_format` is the setroom template naming scheme + include_vanilla
/// flag to emit under. None keeps the previous auto-detect behavior (probe
/// existing templates for `_` vs `-` and default to `_`) so old callers
/// that don't thread the format through stay working.
#[tauri::command]
pub async fn save_custom_level(
    pack: String,
    file_name: String,
    foreground: Vec<Vec<String>>,
    background: Vec<Vec<String>>,
    palette: Vec<SavePaletteEntry>,
    theme: Option<i32>,
    save_format: Option<CustomLevelSaveFormat>,
) -> Result<(), String> {
    let path = resolve_pack_level_path(&pack, &file_name)?;
    if !path.exists() {
        return Err(format!("level not found: {}", path.display()));
    }
    // Validate the format up front so save doesn't half-write the file
    // before erroring out.
    if let Some(ref fmt) = save_format {
        validate_room_template_format(&fmt.room_template_format)?;
    }
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    let sanitized = validate_pack_name(&pack)?;
    let backup_dir = install_dir.join("Mods").join("Backups").join(&sanitized);
    tauri::async_runtime::spawn_blocking(move || {
        save_custom_level_sync(
            path,
            backup_dir,
            foreground,
            background,
            palette,
            theme,
            save_format,
        )
    })
    .await
    .map_err(|e| format!("save task panicked: {e}"))?
}

/// One of vanilla's hard-coded setroom slots. Emitted as an extra
/// `setroomY-X` template alongside the modern `setroomY_X` on save when
/// the pack theme is one of the boss / special themes that vanilla's
/// engine reads via the old naming convention.
#[derive(Debug, Clone, Copy)]
enum VanillaSetroomType {
    /// Front-layer only: mirror emits the OG foreground; bg block omitted.
    Front,
    /// Back-layer only: mirror emits the OG background AS its foreground.
    /// Ice Caves' Mothership section is the canonical case.
    Back,
    /// Both layers: mirror emits OG foreground + OG background, plus the
    /// dual template flag, but only when the OG bg has meaningful content
    /// beyond default hard-floor.
    Dual,
}

/// Returns which vanilla-format setroom to auto-emit for a given
/// (x, y) under a special-theme pack. Preserves the upstream table
/// verbatim, including the couple of dead branches (e.g. Olmec's y==7
/// `elif` is unreachable because y==7 always hits the first `if`) so
/// future audits can diff this against the reference map line-for-line.
///
/// Theme id -> biome name string. The save-time template comment writer
/// stores this string in every setroom's `comment` field so a level
/// opened without a `level_configuration.ls` entry still recovers its
/// theme via the (0,0) template-comment fallback.
///
/// Cosmic Ocean recurses on the subtheme when given; None subtheme +
/// CO falls back to "cave".
fn biome_name_for_theme(theme_id: i32, subtheme_id: Option<i32>) -> &'static str {
    match theme_id {
        1 => "cave",          // Dwelling
        2 => "jungle",        // Jungle
        3 => "volcano",       // Volcana
        4 => "olmec",         // Olmec
        5 | 13 => "tidepool", // Tide Pool / Abzu
        6 => "temple",        // Temple
        7 => "ice",           // Ice Caves
        8 | 14 => "babylon",  // Neo Babylon / Tiamat
        9 | 16 => "sunken",   // Sunken City / Hundun
        10 => {
            // Cosmic Ocean: recurse on subtheme; unset -> cave.
            match subtheme_id {
                Some(s) if s != 10 => biome_name_for_theme(s, None),
                _ => "cave",
            }
        }
        11 => "gold",     // City of Gold
        12 => "duat",     // Duat
        15 => "eggplant", // Eggplant World
        17 => "surface",  // Base Camp
        _ => "cave",
    }
}

/// Inverse of `biome_name_for_theme`: biome name string -> theme id.
/// Powers the load-time fallback that reads the (0,0) setroom
/// template's comment to recover theme for files without a
/// `level_configuration.ls` entry.
///
/// The mapping is one-to-one for the base biomes; Abzu / Tiamat /
/// Hundun -> their non-Abzu counterparts (tidepool / babylon /
/// sunken respectively) since only one biome name maps in this
/// direction.
fn theme_id_for_biome_name(name: &str) -> Option<i32> {
    Some(match name.trim() {
        "cave" => 1,
        "jungle" => 2,
        "volcano" => 3,
        "olmec" => 4,
        "tidepool" => 5,
        "temple" => 6,
        "ice" => 7,
        "babylon" => 8,
        "sunken" => 9,
        "gold" => 11,
        "duat" => 12,
        "eggplant" => 15,
        "surface" => 17,
        _ => return None,
    })
}

fn vanilla_setroom_type_for(theme: i32, x: u32, y: u32) -> Option<VanillaSetroomType> {
    // Theme ints from the game's state.Theme enum; keep in sync with
    // the THEMES table in LevelConfigPanel.tsx.
    const OLMEC: i32 = 4;
    const ICE_CAVES: i32 = 7;
    const DUAT: i32 = 12;
    const ABZU: i32 = 13;
    const TIAMAT: i32 = 14;
    const EGGPLANT_WORLD: i32 = 15;
    const HUNDUN: i32 = 16;

    match theme {
        ICE_CAVES => {
            if (4..=7).contains(&y) && (0..=2).contains(&x) {
                return Some(VanillaSetroomType::Dual);
            }
            if (10..=13).contains(&y) && (0..=2).contains(&x) {
                return Some(VanillaSetroomType::Back);
            }
        }
        TIAMAT => {
            if y == 0 && (0..=2).contains(&x) {
                return Some(VanillaSetroomType::Dual);
            }
            if (2..=10).contains(&y) && (0..=2).contains(&x) {
                return Some(VanillaSetroomType::Front);
            }
        }
        DUAT => {
            if (0..=3).contains(&y) && (0..=2).contains(&x) {
                return Some(VanillaSetroomType::Front);
            }
        }
        EGGPLANT_WORLD => {
            if (0..=1).contains(&y) && (0..=3).contains(&x) {
                return Some(VanillaSetroomType::Front);
            }
        }
        OLMEC => {
            let dual = ([0, 1, 6, 7].contains(&y) && (0..=4).contains(&x))
                || ((2..=5).contains(&y) && [1, 2, 3].contains(&x));
            if dual {
                return Some(VanillaSetroomType::Dual);
            }
            let front =
                ((2..=5).contains(&y) && [0, 4].contains(&x)) || (y == 7 && (0..=4).contains(&x));
            if front {
                return Some(VanillaSetroomType::Front);
            }
        }
        HUNDUN => {
            if [0, 1, 2, 10, 11].contains(&y) && (0..=2).contains(&x) {
                return Some(VanillaSetroomType::Front);
            }
        }
        ABZU => {
            if (0..=3).contains(&y) && (0..=3).contains(&x) {
                return Some(VanillaSetroomType::Dual);
            }
            if (4..=8).contains(&y) && (0..=3).contains(&x) {
                return Some(VanillaSetroomType::Front);
            }
        }
        _ => {}
    }
    None
}

fn save_custom_level_sync(
    path: PathBuf,
    backup_dir: PathBuf,
    foreground: Vec<Vec<String>>,
    background: Vec<Vec<String>>,
    palette: Vec<SavePaletteEntry>,
    theme: Option<i32>,
    save_format: Option<CustomLevelSaveFormat>,
) -> Result<(), String> {
    let mut level = LevelFile::from_path(&path).map_err(|e| e.to_string())?;

    // Explicit format wins over auto-detect. When None, fall back to
    // the legacy underscore-vs-dash probe so old save callsites and
    // files authored by tools that don't thread a format through
    // keep working.
    let (room_template_format, include_vanilla_setrooms) = match save_format {
        Some(fmt) => (fmt.room_template_format, fmt.include_vanilla_setrooms),
        None => {
            let mut use_underscore = true;
            let mut saw_setroom = false;
            for tpl in level.level_templates.all() {
                if let Some(rest) = tpl.name.strip_prefix("setroom") {
                    saw_setroom = true;
                    if rest.contains('_') {
                        use_underscore = true;
                        break;
                    }
                    if rest.contains('-') {
                        use_underscore = false;
                    }
                }
            }
            if !saw_setroom {
                use_underscore = true;
            }
            let fmt = if use_underscore {
                "setroom{y}_{x}"
            } else {
                "setroom{y}-{x}"
            };
            // Match the built-in include_vanilla policy: LevelSequence
            // packs get mirrors, vanilla-format packs don't.
            (fmt.to_string(), use_underscore)
        }
    };

    // Rebuild TileCodes from the palette the frontend sent. Preserves
    // the section comment.
    let mut new_tile_codes = TileCodes::new();
    new_tile_codes.comment = level.tile_codes.comment.clone();
    for p in &palette {
        new_tile_codes.set(TileCode {
            name: p.name.clone(),
            value: p.code.clone(),
            comment: p.comment.clone(),
        });
    }
    level.tile_codes = new_tile_codes;

    // Build name -> code lookup for grid serialization.
    let mut name_to_code: std::collections::HashMap<String, char> =
        std::collections::HashMap::new();
    for p in &palette {
        if let Some(ch) = p.code.chars().next() {
            name_to_code.insert(p.name.clone(), ch);
        }
    }
    // Empty fallback: real "empty" code from palette if present, else '0'.
    let empty_code = name_to_code.get("empty").copied().unwrap_or('0');

    // Grid dimensions from the incoming foreground. Assume 10-wide, 8-tall
    // rooms; short rows/columns get padded with empty on write.
    let width_tiles = foreground.first().map(|r| r.len()).unwrap_or(0);
    let height_tiles = foreground.len();
    let width_rooms = ((width_tiles as u32) / ROOM_TILE_W).max(1);
    let height_rooms = ((height_tiles as u32) / ROOM_TILE_H).max(1);

    // Rebuild LevelTemplates. Preserves the section comment; drops any
    // stale non-setroom templates the file had (custom levels don't
    // use them).
    let mut new_templates = LevelTemplates::new();
    new_templates.comment = level.level_templates.comment.clone();
    // "Empty" background at a cell is either the palette empty name or a
    // literal blank string coming out of the frontend when the author has
    // never touched that cell in the back layer view. Both mean "skip".
    let is_bg_cell_empty = |name: &String| name.is_empty() || name == "empty";
    for y in 0..height_rooms {
        for x in 0..width_rooms {
            let base_row = (y * ROOM_TILE_H) as usize;
            let base_col = (x * ROOM_TILE_W) as usize;
            let mut room_fg: Vec<Vec<char>> = Vec::with_capacity(ROOM_TILE_H as usize);
            let mut room_bg: Vec<Vec<char>> = Vec::with_capacity(ROOM_TILE_H as usize);
            let mut any_bg_placed = false;
            for r in 0..(ROOM_TILE_H as usize) {
                let mut fg_row: Vec<char> = Vec::with_capacity(ROOM_TILE_W as usize);
                let mut bg_row: Vec<char> = Vec::with_capacity(ROOM_TILE_W as usize);
                for c in 0..(ROOM_TILE_W as usize) {
                    let fg_name = foreground
                        .get(base_row + r)
                        .and_then(|rr| rr.get(base_col + c));
                    let fg_ch = fg_name
                        .and_then(|n| name_to_code.get(n))
                        .copied()
                        .unwrap_or(empty_code);
                    fg_row.push(fg_ch);
                    let bg_name = background
                        .get(base_row + r)
                        .and_then(|rr| rr.get(base_col + c));
                    let bg_ch = match bg_name {
                        Some(n) if !is_bg_cell_empty(n) => {
                            any_bg_placed = true;
                            name_to_code.get(n).copied().unwrap_or(empty_code)
                        }
                        _ => empty_code,
                    };
                    bg_row.push(bg_ch);
                }
                room_fg.push(fg_row);
                room_bg.push(bg_row);
            }
            // Only emit the bg layer + dual flag when the author actually
            // placed something in it. Skips the auto-created "empty" bg from
            // level views the user never touched.
            let (bg_out, settings) = if any_bg_placed {
                (room_bg, vec![ml2_levels::TemplateSetting::Dual])
            } else {
                (Vec::new(), Vec::new())
            };
            let room = Room {
                comment: None,
                settings,
                foreground: room_fg,
                background: bg_out,
            };
            let name = format_setroom_name(&room_template_format, y, x);
            // Persist the biome name in every setroom's comment so a
            // `level_configuration.ls`-less file still recovers its
            // theme on next open via the (0,0) template-comment
            // fallback.
            let biome_comment = theme.map(|t| biome_name_for_theme(t, None).to_string());
            new_templates.set(LevelTemplate {
                name,
                comment: biome_comment,
                rooms: vec![room],
            });
        }
    }

    // Vanilla-setroom mirror pass. Runs when the chosen save format opted
    // into it (include_vanilla_setrooms) AND the theme is one of the boss
    // / special ones vanilla's engine reads out of the old dash-format
    // template slots. The mirror lets a modern .lvl still play correctly
    // on those themes; without it the game falls back to default room
    // layouts at the hard-coded coordinates.
    if include_vanilla_setrooms && let Some(theme_int) = theme {
        let hard_floor_code_opt = name_to_code.get("floor_hard").copied();
        let hard_floor_code = hard_floor_code_opt.unwrap_or('X');
        // Extract the same fg/bg chunks the main loop would build
        // for any (y, x), including out-of-bounds coords: those
        // synthesize air fg + hard-floor bg to fill coords the
        // user's level doesn't cover.
        let room_chunks = |y: u32, x: u32| -> (Vec<Vec<char>>, Vec<Vec<char>>) {
            let base_row = (y * ROOM_TILE_H) as usize;
            let base_col = (x * ROOM_TILE_W) as usize;
            let in_bounds = y < height_rooms && x < width_rooms;
            let mut fg: Vec<Vec<char>> = Vec::with_capacity(ROOM_TILE_H as usize);
            let mut bg: Vec<Vec<char>> = Vec::with_capacity(ROOM_TILE_H as usize);
            for r in 0..(ROOM_TILE_H as usize) {
                let mut fg_row: Vec<char> = Vec::with_capacity(ROOM_TILE_W as usize);
                let mut bg_row: Vec<char> = Vec::with_capacity(ROOM_TILE_W as usize);
                for c in 0..(ROOM_TILE_W as usize) {
                    let (fg_ch, bg_ch) = if in_bounds {
                        let fg_name = foreground
                            .get(base_row + r)
                            .and_then(|rr| rr.get(base_col + c));
                        let fg_ch = fg_name
                            .and_then(|n| name_to_code.get(n))
                            .copied()
                            .unwrap_or(empty_code);
                        let bg_name = background
                            .get(base_row + r)
                            .and_then(|rr| rr.get(base_col + c));
                        let bg_ch = match bg_name {
                            Some(n) if !is_bg_cell_empty(n) => {
                                name_to_code.get(n).copied().unwrap_or(empty_code)
                            }
                            _ => empty_code,
                        };
                        (fg_ch, bg_ch)
                    } else {
                        (empty_code, hard_floor_code)
                    };
                    fg_row.push(fg_ch);
                    bg_row.push(bg_ch);
                }
                fg.push(fg_row);
                bg.push(bg_row);
            }
            (fg, bg)
        };
        // "Trivial bg" == every cell is the hard-floor tile. Only
        // meaningful when hard_floor is actually in the palette;
        // otherwise every bg is considered meaningful.
        let bg_is_trivial = |bg: &[Vec<char>]| -> bool {
            hard_floor_code_opt.is_some()
                && bg
                    .iter()
                    .all(|row| row.iter().all(|&c| c == hard_floor_code))
        };
        // Iterate every coord vanilla's engine might read from,
        // capped at 8 columns and 15 rows. Rooms that don't have a
        // special-theme mapping short-circuit early so most
        // iterations do no work.
        for y in 0..15u32 {
            for x in 0..8u32 {
                let Some(kind) = vanilla_setroom_type_for(theme_int, x, y) else {
                    continue;
                };
                let (og_fg, og_bg) = room_chunks(y, x);
                let og_name = format_setroom_name(&room_template_format, y, x);
                let (mirror_fg, mirror_bg, mirror_settings, label) = match kind {
                    VanillaSetroomType::Front => (og_fg, Vec::new(), Vec::new(), "the front layer"),
                    VanillaSetroomType::Back => {
                        // Vanilla reads the OG's back layer as its own
                        // front, so the mirror's fg is the OG bg.
                        (og_bg, Vec::new(), Vec::new(), "the back layer")
                    }
                    VanillaSetroomType::Dual => {
                        if bg_is_trivial(&og_bg) {
                            (og_fg, Vec::new(), Vec::new(), "both layers")
                        } else {
                            (
                                og_fg,
                                og_bg,
                                vec![ml2_levels::TemplateSetting::Dual],
                                "both layers",
                            )
                        }
                    }
                };
                let comment = Some(format!(
                    "Auto-generated template to match {label} of {og_name}."
                ));
                new_templates.set(LevelTemplate {
                    name: format!("setroom{y}-{x}"),
                    comment,
                    rooms: vec![Room {
                        comment: None,
                        settings: mirror_settings,
                        foreground: mirror_fg,
                        background: mirror_bg,
                    }],
                });
            }
        }
    }

    level.level_templates = new_templates;

    // Update size setting, preserving the existing comment if present.
    let size_comment = level
        .level_settings
        .get("size")
        .and_then(|s| s.comment.clone());
    ensure_size_setting(
        &mut level.level_settings,
        width_rooms,
        height_rooms,
        size_comment,
    );

    // Backup + write. Backup errors are logged but not fatal so the save
    // still lands; write errors abort so the file isn't left half-updated.
    if let Err(e) = make_backup(&path, &backup_dir) {
        tracing::warn!(target: "level_editor", "backup failed for {}: {}", path.display(), e);
    }
    level.write_path(&path).map_err(|e| e.to_string())?;
    Ok(())
}

fn ensure_size_setting(settings: &mut LevelSettings, w: u32, h: u32, comment: Option<String>) {
    settings.set(LevelSetting {
        name: "size".to_string(),
        value: LevelSettingValue::Size(w.to_string(), h.to_string()),
        comment,
    });
}

// --- Custom level CRUD ------------------------------------------------------

/// Level settings that get zeroed out on a fresh level so spawn-related
/// systems (back layer generation, decor spread, special rooms, mounts,
/// ...) stay off until the author opts in.
const DEFAULT_ZERO_LEVEL_SETTINGS: &[&str] = &[
    "altar_room_chance",
    "back_room_chance",
    "back_room_hidden_door_cache_chance",
    "back_room_hidden_door_chance",
    "back_room_interconnection_chance",
    "background_chance",
    "flagged_liquid_rooms",
    "floor_bottom_spread_chance",
    "floor_side_spread_chance",
    "ground_background_chance",
    "idol_room_chance",
    "machine_bigroom_chance",
    "machine_rewardroom_chance",
    "machine_tallroom_chance",
    "machine_wideroom_chance",
    "max_liquid_particles",
    "mount_chance",
];

fn validate_lvl_file_name(name: &str) -> Result<String, String> {
    let trimmed = name.trim();
    if trimmed.is_empty() {
        return Err("file name is empty".into());
    }
    if trimmed.contains('/')
        || trimmed.contains('\\')
        || trimmed.contains("..")
        || trimmed.starts_with('.')
    {
        return Err(format!("invalid file name: {trimmed:?}"));
    }
    let with_ext = if trimmed.to_lowercase().ends_with(".lvl") {
        trimmed.to_string()
    } else {
        format!("{trimmed}.lvl")
    };
    Ok(with_ext)
}

/// Validate a setroom template string. Must contain exactly one `{y}`
/// and one `{x}` placeholder and no other `{...}` sequences, so callers
/// can safely substitute both.
fn validate_room_template_format(fmt: &str) -> Result<(), String> {
    let y_count = fmt.matches("{y}").count();
    let x_count = fmt.matches("{x}").count();
    if y_count != 1 || x_count != 1 {
        return Err(format!(
            "room template must contain exactly one {{y}} and one {{x}}: {fmt:?}"
        ));
    }
    // Strip the recognised placeholders and reject any leftover braces so
    // typos like {yx} or an empty {} don't sneak through as literals.
    let stripped = fmt.replacen("{y}", "", 1).replacen("{x}", "", 1);
    if stripped.contains('{') || stripped.contains('}') {
        return Err(format!("room template has stray braces: {fmt:?}"));
    }
    Ok(())
}

fn format_setroom_name(fmt: &str, y: u32, x: u32) -> String {
    fmt.replacen("{y}", &y.to_string(), 1)
        .replacen("{x}", &x.to_string(), 1)
}

/// Creates a blank `.lvl` under the pack with a minimal palette (floor,
/// empty, floor_hard) and hard-floor background across every room.
/// `room_template_format` picks the naming scheme (`setroom{y}_{x}` for
/// LevelSequence, `setroom{y}-{x}` for vanilla, or any user-defined
/// pattern containing both placeholders). Fails if the target file
/// already exists.
#[tauri::command]
pub async fn create_custom_level(
    pack: String,
    file_name: String,
    width_rooms: u32,
    height_rooms: u32,
    room_template_format: String,
) -> Result<String, String> {
    let sanitized_pack = validate_pack_name(&pack)?;
    let file_name = validate_lvl_file_name(&file_name)?;
    validate_room_template_format(&room_template_format)?;
    if width_rooms == 0 || height_rooms == 0 {
        return Err("width and height must be at least 1 room".into());
    }
    let levels_dir = packs_dir()?
        .join(&sanitized_pack)
        .join("Data")
        .join("Levels");
    let path = levels_dir.join(&file_name);
    if path.exists() {
        return Err(format!("level {file_name:?} already exists"));
    }

    tauri::async_runtime::spawn_blocking(move || {
        std::fs::create_dir_all(&levels_dir)
            .map_err(|e| format!("mkdir {}: {e}", levels_dir.display()))?;
        write_blank_level(&path, width_rooms, height_rooms, &room_template_format)?;
        Ok::<String, String>(file_name)
    })
    .await
    .map_err(|e| format!("create task panicked: {e}"))?
}

fn write_blank_level(
    path: &std::path::Path,
    w_rooms: u32,
    h_rooms: u32,
    room_template_format: &str,
) -> Result<(), String> {
    let mut level = LevelFile::default();

    // Seed the palette with three baseline tiles. Any tile the author
    // adds later goes through save_custom_level, which reuses the
    // caller's palette wholesale.
    let seed_tiles: &[(&str, &str)] = &[("floor", "1"), ("empty", "0"), ("floor_hard", "X")];
    for (name, code) in seed_tiles {
        level.tile_codes.set(TileCode {
            name: (*name).to_string(),
            value: (*code).to_string(),
            comment: None,
        });
    }

    // Zero out every spawn-related chance so a brand-new level doesn't
    // spontaneously generate back layers, special rooms, mount encounters,
    // etc. Author opts back in via the level rules panel.
    for name in DEFAULT_ZERO_LEVEL_SETTINGS {
        level.level_settings.set(LevelSetting {
            name: (*name).to_string(),
            value: LevelSettingValue::Int(0),
            comment: None,
        });
    }
    ensure_size_setting(&mut level.level_settings, w_rooms, h_rooms, None);

    // Build one setroom per (y, x). Foreground is all-empty; background is
    // hard-floor. The DUAL settings flag marks the room as dual so the game
    // actually renders the bg layer.
    for y in 0..h_rooms {
        for x in 0..w_rooms {
            let fg_row = vec!['0'; ROOM_TILE_W as usize];
            let bg_row = vec!['X'; ROOM_TILE_W as usize];
            let foreground = vec![fg_row; ROOM_TILE_H as usize];
            let background = vec![bg_row; ROOM_TILE_H as usize];
            let room = Room {
                comment: None,
                settings: vec![ml2_levels::TemplateSetting::Dual],
                foreground,
                background,
            };
            level.level_templates.set(LevelTemplate {
                name: format_setroom_name(room_template_format, y, x),
                comment: None,
                rooms: vec![room],
            });
        }
    }

    level.write_path(path).map_err(|e| e.to_string())?;
    Ok(())
}

/// Renames a level file within the pack. Both names go through the same
/// validation as create/save so an accidental `..` can't escape the pack
/// dir. Fails if the target already exists.
#[tauri::command]
pub fn rename_custom_level(
    pack: String,
    old_file_name: String,
    new_file_name: String,
) -> Result<String, String> {
    let old_path = resolve_pack_level_path(&pack, &old_file_name)?;
    if !old_path.exists() {
        return Err(format!("level not found: {}", old_path.display()));
    }
    let new_file_name = validate_lvl_file_name(&new_file_name)?;
    let sanitized_pack = validate_pack_name(&pack)?;
    let levels_dir = packs_dir()?
        .join(&sanitized_pack)
        .join("Data")
        .join("Levels");
    let new_path = levels_dir.join(&new_file_name);
    if new_path.exists() {
        return Err(format!("level {new_file_name:?} already exists"));
    }
    std::fs::rename(&old_path, &new_path).map_err(|e| {
        format!(
            "rename {} -> {}: {e}",
            old_path.display(),
            new_path.display()
        )
    })?;
    Ok(new_file_name)
}

/// Deletes a level file after moving a timestamped copy into the pack's
/// backups directory. The backup lets the user recover from an accidental
/// click; delete is otherwise a permanent, disk-touching action.
#[tauri::command]
pub fn delete_custom_level(pack: String, file_name: String) -> Result<(), String> {
    let path = resolve_pack_level_path(&pack, &file_name)?;
    if !path.exists() {
        return Err(format!("level not found: {}", path.display()));
    }
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    let sanitized = validate_pack_name(&pack)?;
    let backup_dir = install_dir.join("Mods").join("Backups").join(&sanitized);
    if let Err(e) = make_backup(&path, &backup_dir) {
        tracing::warn!(target: "level_editor", "backup failed for {}: {}", path.display(), e);
    }
    std::fs::remove_file(&path).map_err(|e| format!("delete {}: {e}", path.display()))?;
    Ok(())
}

const MAX_BACKUPS: usize = 50;

/// Copies `source` into `backup_dir` with a unix-timestamp suffix
/// (per-file backup dir, capped history). Prunes oldest backups above
/// `MAX_BACKUPS`.
fn make_backup(source: &std::path::Path, backup_dir: &std::path::Path) -> Result<(), String> {
    if !source.exists() {
        return Ok(());
    }
    std::fs::create_dir_all(backup_dir)
        .map_err(|e| format!("mkdir {}: {e}", backup_dir.display()))?;

    let stem = source
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("level");
    let ext = source.extension().and_then(|s| s.to_str()).unwrap_or("lvl");
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let backup_path = backup_dir.join(format!("{stem}_{secs}.{ext}"));
    std::fs::copy(source, &backup_path).map_err(|e| format!("backup copy: {e}"))?;

    prune_old_backups(backup_dir, MAX_BACKUPS)?;
    Ok(())
}

fn prune_old_backups(dir: &std::path::Path, keep: usize) -> Result<(), String> {
    let entries = std::fs::read_dir(dir).map_err(|e| e.to_string())?;
    let mut files: Vec<(std::path::PathBuf, std::time::SystemTime)> = Vec::new();
    for entry in entries {
        let Ok(entry) = entry else { continue };
        let Ok(meta) = entry.metadata() else { continue };
        if !meta.is_file() {
            continue;
        }
        let ctime = meta
            .created()
            .or_else(|_| meta.modified())
            .unwrap_or(std::time::UNIX_EPOCH);
        files.push((entry.path(), ctime));
    }
    if files.len() <= keep {
        return Ok(());
    }
    files.sort_by_key(|(_, t)| *t);
    for (path, _) in files.iter().take(files.len() - keep) {
        let _ = std::fs::remove_file(path);
    }
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn place_template(
    fg_grid: &mut [Vec<String>],
    bg_grid: &mut [Vec<String>],
    tpl: &ml2_levels::LevelTemplate,
    x: u32,
    y: u32,
    code_to_name: &std::collections::HashMap<char, String>,
    placed: &mut std::collections::HashSet<(u32, u32)>,
    width_rooms: u32,
    height_rooms: u32,
) {
    if x >= width_rooms || y >= height_rooms {
        return;
    }
    if placed.contains(&(x, y)) {
        return;
    }
    let Some(room) = tpl.rooms.first() else {
        return;
    };
    let base_col = (x * ROOM_TILE_W) as usize;
    let base_row = (y * ROOM_TILE_H) as usize;
    let copy_room_layer = |dst: &mut [Vec<String>], src: &[Vec<char>]| {
        for (r, row_chars) in src.iter().enumerate() {
            for (c, ch) in row_chars.iter().enumerate() {
                let grid_r = base_row + r;
                let grid_c = base_col + c;
                if grid_r < dst.len() && grid_c < dst[grid_r].len() {
                    let name = code_to_name.get(ch).cloned().unwrap_or_default();
                    dst[grid_r][grid_c] = name;
                }
            }
        }
    };
    copy_room_layer(fg_grid, &room.foreground);
    // A non-dual template omits the bg layer entirely (`room.background` is
    // empty). Skip the copy so bg stays as its all-empty seed, which the
    // editor reads as "no back layer here".
    if !room.background.is_empty() {
        copy_room_layer(bg_grid, &room.background);
    }
    placed.insert((x, y));
}

/// Builds an atlas for a set of tile-code NAMES. Each name is looked up
/// against `ml2_sprites::all_loaders()` for a chunk with that name in
/// its `chunk_map`; on hit, the sub-image is cropped out of the
/// corresponding biome/entity sprite sheet on disk. Names that don't
/// resolve (community tile codes, unknown entities, etc.) get a
/// hashed-color placeholder with the name stamped on top so they're
/// still visible.
///
/// `biome` is an optional priority hint. If set, that biome's floor sheet
/// wins over other loaders that also carry the same name.
#[tauri::command]
pub async fn build_tile_name_atlas(
    names: Vec<String>,
    biome: Option<String>,
) -> Result<EditorAtlas, String> {
    if names.is_empty() {
        return Err("no tile names provided".into());
    }
    // Locate the extract dir up front so the blocking task doesn't need
    // the async runtime for it.
    let extract_dir = crate::config::load()
        .install_dir
        .map(|d| d.join("Mods").join("Extracted"));
    tauri::async_runtime::spawn_blocking(move || {
        build_tile_name_atlas_sync(names, biome, extract_dir)
    })
    .await
    .map_err(|e| format!("atlas task panicked: {e}"))?
}

const ATLAS_TILE_CELL: u32 = 64;

/// Loader-name priority for a given biome hint. First match wins so
/// the biome-specific floor sheet is picked over generic ones that
/// also carry the tile.
///
/// TilecodeExtras always heads the list. The bundled PNG carries
/// editor-only art for `entrance`, `exit`, `entrance_shortcut`,
/// `yellowdoor`, `doorred`, `doorpurple`, etc. that must win over the
/// game's per-biome floor sheet copies. Tiles TilecodeExtras doesn't
/// carry fall through to the biome list below.
///
/// Order per biome (after TilecodeExtras): `<Floor sheet>`,
/// `<Floorstyled sheet>`, `<Deco sheet>`. A few non-default biomes
/// (olmec, duat, gold, beehive) don't have their own floor sheet;
/// delegate to a sibling biome's floor art (jungle for olmec/beehive,
/// temple for duat/gold).
fn biome_priority(biome: Option<&str>) -> Vec<&'static str> {
    let mut priority = vec!["TilecodeExtras"];
    priority.extend(match biome {
        Some("cave") => ["CaveFloorSheet", "WoodStyledFloorSheet", "CaveDecoSheet"],
        Some("jungle") => [
            "JungleFloorSheet",
            "StonedStyledFloorSheet",
            "JungleDecoSheet",
        ],
        Some("volcano") => [
            "VolcanaFloorSheet",
            "VladStyledFloorSheet",
            "VolcanaDecoSheet",
        ],
        Some("olmec") => [
            "JungleFloorSheet",
            "StonedStyledFloorSheet",
            "JungleDecoSheet",
        ],
        Some("tidepool") => [
            "TidePoolFloorSheet",
            "PagodaStyledFloorSheet",
            "TidePoolDecoSheet",
        ],
        Some("temple") => [
            "TempleFloorSheet",
            "TempleStyledFloorSheet",
            "TempleDecoSheet",
        ],
        Some("duat") => [
            "TempleFloorSheet",
            "DuatStyledFloorSheet",
            "TempleDecoSheet",
        ],
        Some("gold") => [
            "TempleFloorSheet",
            "GoldStyledFloorSheet",
            "TempleDecoSheet",
        ],
        Some("beehive") => [
            "JungleFloorSheet",
            "HiveStyledFloorSheet",
            "JungleDecoSheet",
        ],
        Some("ice") => [
            "IceCavesFloorSheet",
            "MothershipStyledFloorSheet",
            "IceCavesDecoSheet",
        ],
        Some("babylon") => [
            "BabylonFloorSheet",
            "BabylonStyledFloorSheet",
            "BabylonDecoSheet",
        ],
        Some("sunken") => [
            "SunkenCityFloorSheet",
            "SunkenCityStyledFloorSheet",
            "SunkenCityDecoSheet",
        ],
        Some("eggplant") => [
            "EggplantFloorSheet",
            "StonedStyledFloorSheet",
            "EggplantDecoSheet",
        ],
        Some("surface") => [
            "SurfaceFloorSheet",
            "WoodStyledFloorSheet",
            "SurfaceDecoSheet",
        ],
        // Default: prefer cave for unknown themes.
        _ => ["CaveFloorSheet", "WoodStyledFloorSheet", "CaveDecoSheet"],
    });
    priority
}

fn find_tile_source<'a>(
    all_loaders: &'a [ml2_sprites::LoaderConfig],
    name: &str,
    priority: &[&str],
) -> Option<(&'a ml2_sprites::LoaderConfig, ml2_sprites::ChunkCoords)> {
    for pri in priority {
        for cfg in all_loaders {
            if cfg.name == *pri
                && let Some(coords) = cfg.chunk_map.get(name)
            {
                return Some((cfg, *coords));
            }
        }
    }
    for cfg in all_loaders {
        if let Some(coords) = cfg.chunk_map.get(name) {
            return Some((cfg, *coords));
        }
    }
    None
}

/// PNGs bundled with the app that no game extract will produce: community
/// tile-code sprites plus a couple of sheets the merger overlays on top of
/// extracted game art (`pet_heads.png`). Paths match the `sprite_sheet_path`
/// values in the generated `ml2_sprites` loaders.
static BUNDLED_SHEET_BYTES: &[(&str, &[u8])] = &[
    (
        "static/images/tilecodeextras.png",
        include_bytes!("../resources/tilecode_extras/tilecodeextras.png"),
    ),
    (
        "static/images/chainandblocks_ceiling.png",
        include_bytes!("../resources/tilecode_extras/chainandblocks_ceiling.png"),
    ),
    (
        "static/images/spikeball_trap.png",
        include_bytes!("../resources/tilecode_extras/spikeball_trap.png"),
    ),
    (
        "static/images/sticky_trap.png",
        include_bytes!("../resources/tilecode_extras/sticky_trap.png"),
    ),
    (
        "static/images/treasure_vaultchest.png",
        include_bytes!("../resources/tilecode_extras/treasure_vaultchest.png"),
    ),
    (
        "static/images/venom.png",
        include_bytes!("../resources/tilecode_extras/venom.png"),
    ),
    (
        "static/images/pet_heads.png",
        include_bytes!("../resources/tilecode_extras/pet_heads.png"),
    ),
];

/// Turns a loader's `sprite_sheet_path` into a lookup key. For sheets under
/// the game's extract dir this returns the real filesystem path. For
/// bundled `static/images/*.png` paths this returns a stable virtual path
/// that the sheet cache uses as its key; `load_sheet` decodes the embedded
/// bytes on first miss.
fn resolve_sheet_path(rel: &std::path::Path, extract_dir: Option<&PathBuf>) -> Option<PathBuf> {
    let rel_str = rel.to_string_lossy().replace('\\', "/");
    if rel_str.starts_with("static/images/") {
        return Some(PathBuf::from(format!("embedded://{rel_str}")));
    }
    extract_dir.map(|d| d.join(rel))
}

fn load_sheet(rel: &std::path::Path, path: &std::path::Path) -> Option<image::DynamicImage> {
    let rel_str = rel.to_string_lossy().replace('\\', "/");
    if rel_str.starts_with("static/images/") {
        let bytes = BUNDLED_SHEET_BYTES
            .iter()
            .find(|(name, _)| *name == rel_str)
            .map(|(_, bytes)| *bytes)?;
        return image::load_from_memory(bytes).ok();
    }
    image::open(path).ok()
}

/// Renders one tile as a `CELL x CELL` RGBA image: real sprite if the name
/// resolves in any loader, percent-composite for `foo%NN` or
/// `foo%NN%bar` names, otherwise the hashed-color placeholder with the
/// name stamped on top. Extracted so `get_tile_sprite` and the atlas builder
/// share the same lookup + fallback logic.
fn render_tile_image(
    name: &str,
    all_loaders: &[ml2_sprites::LoaderConfig],
    priority: &[&str],
    extract_dir: Option<&PathBuf>,
    sheet_cache: &mut std::collections::HashMap<PathBuf, Option<image::DynamicImage>>,
) -> RenderedTile {
    // Percent-tile: `foo%50` or `foo%50%bar`. Parsed against the
    // `%\d{1,2}%?` shape; the alt component defaults to `empty` when
    // absent. The composite always clamps back to 1x1 (the percent
    // label + halves are drawn assuming a single cell), so multi-cell
    // natural sizes are dropped intentionally here.
    if let Some((primary, percent, alt)) = parse_percent_name(name) {
        let alt_name = alt.unwrap_or("empty");
        let prim = render_leaf_tile_image(primary, all_loaders, priority, extract_dir, sheet_cache);
        let alt = render_leaf_tile_image(alt_name, all_loaders, priority, extract_dir, sheet_cache);
        // Clamp both halves back to 1x1 before compositing.
        let prim_cell = force_to_cell(prim.image);
        let alt_cell = force_to_cell(alt.image);
        return RenderedTile {
            image: composite_percent_tile(&prim_cell, &alt_cell, percent),
            nat_w_cells: 1,
            nat_h_cells: 1,
        };
    }
    render_leaf_tile_image(name, all_loaders, priority, extract_dir, sheet_cache)
}

/// Resample a tile image to a single ATLAS_TILE_CELL square. Used to clamp
/// multi-cell natural sprites back to 1x1 for the percent-composite path
/// and for the `get_tile_sprite` command (which serves palette swatches
/// that always render in a single cell).
fn force_to_cell(img: image::RgbaImage) -> image::RgbaImage {
    if img.width() == ATLAS_TILE_CELL && img.height() == ATLAS_TILE_CELL {
        return img;
    }
    image::imageops::resize(
        &img,
        ATLAS_TILE_CELL,
        ATLAS_TILE_CELL,
        image::imageops::FilterType::Lanczos3,
    )
}

/// Natural size of a rendered tile in *grid cells*, together with the
/// rendered image. `w == 1 && h == 1` for ordinary tiles; larger values
/// mean the sprite is bigger than a cell and should overflow into
/// neighbours at render time (statues, doors, multi-cell traps, etc).
pub struct RenderedTile {
    pub image: image::RgbaImage,
    pub nat_w_cells: u32,
    pub nat_h_cells: u32,
}

/// The non-percent inner half: real sprite → fallback placeholder. Not
/// recursive. Returns the natural cell size alongside the image so the
/// atlas caller can preserve overflow at render time; every sprite is
/// stored at `nat_cells * ATLAS_TILE_CELL` per axis so up-scaling in
/// PixiJS keeps its native resolution.
fn render_leaf_tile_image(
    name: &str,
    all_loaders: &[ml2_sprites::LoaderConfig],
    priority: &[&str],
    extract_dir: Option<&PathBuf>,
    sheet_cache: &mut std::collections::HashMap<PathBuf, Option<image::DynamicImage>>,
) -> RenderedTile {
    use image::{ImageBuffer, Rgba};

    let real = find_tile_source(all_loaders, name, priority).and_then(|(cfg, coords)| {
        let path = resolve_sheet_path(&cfg.sprite_sheet_path, extract_dir)?;
        let sheet_slot = sheet_cache
            .entry(path.clone())
            .or_insert_with(|| load_sheet(&cfg.sprite_sheet_path, &path));
        let sheet = sheet_slot.as_ref()?;
        let cs = cfg.chunk_size as f32;
        let x = (coords.0 * cs).round() as u32;
        let y = (coords.1 * cs).round() as u32;
        let w = ((coords.2 - coords.0) * cs).round() as u32;
        let h = ((coords.3 - coords.1) * cs).round() as u32;
        if x + w > sheet.width() || y + h > sheet.height() || w == 0 || h == 0 {
            return None;
        }
        use image::GenericImageView;
        let crop = sheet.view(x, y, w, h).to_image();
        // Chunks are square, so the sprite's cell footprint is just
        // (w / cs, h / cs) rounded up. Wide/tall sprites keep their
        // aspect at ATLAS_TILE_CELL per cell.
        let cs_u = cfg.chunk_size;
        let nat_w = ((w as f32 / cs_u as f32).ceil() as u32).max(1);
        let nat_h = ((h as f32 / cs_u as f32).ceil() as u32).max(1);
        let target_w = nat_w * ATLAS_TILE_CELL;
        let target_h = nat_h * ATLAS_TILE_CELL;
        let resized = image::imageops::resize(
            &crop,
            target_w,
            target_h,
            image::imageops::FilterType::Lanczos3,
        );
        Some(RenderedTile {
            image: resized,
            nat_w_cells: nat_w,
            nat_h_cells: nat_h,
        })
    });

    if let Some(rt) = real {
        return rt;
    }
    // Placeholder: render at 4x the atlas cell size so text stays sharp
    // when the user zooms in. Real sprites cap at ATLAS_TILE_CELL because
    // the source art is 128px per game tile and downscaled once during
    // atlas build; placeholders are pure vector text so there's no
    // fidelity ceiling to preserve, and the extra source pixels turn
    // 800% zoom from a 6x upscale into ~1.5x. `nat_*_cells = 1` keeps
    // the sprite one game tile in world space; only the sampler sees
    // the higher resolution.
    const PLACEHOLDER_UPSCALE: u32 = 4;
    let size = ATLAS_TILE_CELL * PLACEHOLDER_UPSCALE;
    let color = color_for_name(name);
    let mut img: image::RgbaImage =
        ImageBuffer::from_pixel(size, size, Rgba([color[0], color[1], color[2], 255]));
    stamp_name_label(&mut img, name);
    RenderedTile {
        image: img,
        nat_w_cells: 1,
        nat_h_cells: 1,
    }
}

/// Parses `foo%50` or `foo%50%bar` into `(primary, percent, Some(alt))`
/// or `(primary, percent, None)`. Returns None if the name has no
/// percent component (recognised shape: `%\d{1,2}%?`).
fn parse_percent_name(name: &str) -> Option<(&str, u8, Option<&str>)> {
    let idx = name.find('%')?;
    let (primary, rest) = name.split_at(idx);
    // Skip the leading '%'
    let after = &rest[1..];
    // Take up to two ASCII digits.
    let digit_end = after
        .bytes()
        .take_while(|b| b.is_ascii_digit())
        .count()
        .min(2);
    if digit_end == 0 {
        return None;
    }
    let percent: u8 = after[..digit_end].parse().ok()?;
    let tail = &after[digit_end..];
    let alt = if let Some(stripped) = tail.strip_prefix('%') {
        if stripped.is_empty() {
            None
        } else {
            Some(stripped)
        }
    } else if tail.is_empty() {
        None
    } else {
        // Something after the digits that isn't a `%`; not a well-formed
        // percent name.
        return None;
    };
    Some((primary, percent, alt))
}

/// Composites two `ATLAS_TILE_CELL` images along the top-right → bottom-left
/// diagonal (primary in the upper-left triangle, alt in the lower-right)
/// and stamps a small "NN" label at the bottom-left corner so the split
/// ratio is obvious at a glance.
fn composite_percent_tile(
    primary: &image::RgbaImage,
    alt: &image::RgbaImage,
    percent: u8,
) -> image::RgbaImage {
    use image::{ImageBuffer, Rgba};
    let cell = ATLAS_TILE_CELL as i32;
    let mut out: image::RgbaImage = ImageBuffer::new(cell as u32, cell as u32);
    for y in 0..cell {
        for x in 0..cell {
            let src = if x + y < cell { primary } else { alt };
            let px = *src.get_pixel(x as u32, y as u32);
            out.put_pixel(x as u32, y as u32, px);
        }
    }
    // Diagonal separator line for readability.
    for i in 0..cell {
        let x = i as u32;
        let y = (cell - 1 - i) as u32;
        if x < out.width() && y < out.height() {
            out.put_pixel(x, y, Rgba([0, 0, 0, 200]));
        }
    }
    // Percent label at bottom-left, drawn 3x larger than the tile-name
    // glyphs so the ratio reads at a glance on a 64x64 swatch.
    stamp_percent_label(&mut out, percent, cell);
    out
}

/// Draws the percent value using the 3x5 glyph font scaled up 3x with a
/// black backing block, at the bottom-left corner of the tile.
fn stamp_percent_label(img: &mut image::RgbaImage, percent: u8, cell: i32) {
    use image::Rgba;
    let text = format!("{percent}");
    let scale = 3;
    let char_w = 3 * scale;
    let char_h = 5 * scale;
    let gap = scale;
    let pad = 2;
    let total_w = text.len() as i32 * (char_w + gap) - gap + pad * 2;
    let total_h = char_h + pad * 2;
    let x0 = 2;
    let y0 = cell - total_h - 2;

    for dy in 0..total_h {
        for dx in 0..total_w {
            let px = x0 + dx;
            let py = y0 + dy;
            if px >= 0 && py >= 0 && px < cell && py < cell {
                img.put_pixel(px as u32, py as u32, Rgba([0, 0, 0, 200]));
            }
        }
    }
    let mut cursor_x = x0 + pad;
    let text_y = y0 + pad;
    for ch in text.chars() {
        draw_scaled_glyph(img, ch, cursor_x, text_y, scale);
        cursor_x += char_w + gap;
    }
}

/// Same 3x5 glyph, but each source pixel becomes a `scale x scale` block.
/// Uses a warm yellow so the number pops against dark bg + darker tiles.
fn draw_scaled_glyph(img: &mut image::RgbaImage, ch: char, x: i32, y: i32, scale: i32) {
    let pattern = glyph_pattern(ch.to_ascii_lowercase());
    let color = image::Rgba([255, 220, 90, 255]);
    for (dy, row) in pattern.iter().enumerate() {
        for dx in 0..3 {
            if row & (1 << (2 - dx)) != 0 {
                for sy in 0..scale {
                    for sx in 0..scale {
                        let px = x + dx * scale + sx;
                        let py = y + dy as i32 * scale + sy;
                        if px >= 0 && py >= 0 && px < img.width() as i32 && py < img.height() as i32
                        {
                            img.put_pixel(px as u32, py as u32, color);
                        }
                    }
                }
            }
        }
    }
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TileSprite {
    /// Data URL: `data:image/png;base64,...`. Client feeds it straight into
    /// an HTMLImageElement and then a PixiJS texture.
    pub png_data_url: String,
    pub tile_size: u32,
}

/// Returns just one tile as a PNG data URL, at the same CELL size the atlas
/// builder uses. Used by the frontend to extend an already-loaded canvas
/// with a newly-added palette tile without paying for a full atlas rebuild.
#[tauri::command]
pub async fn get_tile_sprite(name: String, biome: Option<String>) -> Result<TileSprite, String> {
    let extract_dir = crate::config::load()
        .install_dir
        .map(|d| d.join("Mods").join("Extracted"));
    tauri::async_runtime::spawn_blocking(move || get_tile_sprite_sync(name, biome, extract_dir))
        .await
        .map_err(|e| format!("sprite task panicked: {e}"))?
}

fn get_tile_sprite_sync(
    name: String,
    biome: Option<String>,
    extract_dir: Option<PathBuf>,
) -> Result<TileSprite, String> {
    use image::codecs::png::{CompressionType, FilterType, PngEncoder};
    use image::{ColorType, ImageEncoder};

    let all_loaders = ml2_sprites::all_loaders();
    let priority = biome_priority(biome.as_deref());
    let mut sheet_cache = std::collections::HashMap::new();
    let rendered = render_tile_image(
        &name,
        &all_loaders,
        &priority,
        extract_dir.as_ref(),
        &mut sheet_cache,
    );
    // Palette swatches always render in a single cell; clamp any natural
    // overflow back to ATLAS_TILE_CELL before shipping.
    let img = force_to_cell(rendered.image);

    // Fast compression here: it's one 64x64 tile shipped to the frontend,
    // not the shared atlas that lives in memory for the session.
    let mut png_bytes = Vec::new();
    {
        let mut cursor = std::io::Cursor::new(&mut png_bytes);
        PngEncoder::new_with_quality(&mut cursor, CompressionType::Default, FilterType::Adaptive)
            .write_image(
                img.as_raw(),
                img.width(),
                img.height(),
                ColorType::Rgba8.into(),
            )
            .map_err(|e| e.to_string())?;
    }

    let mut png_data_url = String::from("data:image/png;base64,");
    STANDARD.encode_string(&png_bytes, &mut png_data_url);

    Ok(TileSprite {
        png_data_url,
        tile_size: ATLAS_TILE_CELL,
    })
}

fn build_tile_name_atlas_sync(
    names: Vec<String>,
    biome: Option<String>,
    extract_dir: Option<PathBuf>,
) -> Result<EditorAtlas, String> {
    use image::DynamicImage;

    let all_loaders = ml2_sprites::all_loaders();
    let priority = biome_priority(biome.as_deref());
    // Cache opened sprite sheets so N tiles from the same sheet only pay
    // for one file open + decode.
    let mut sheet_cache: std::collections::HashMap<PathBuf, Option<DynamicImage>> =
        std::collections::HashMap::new();

    let mut inputs = Vec::with_capacity(names.len());
    // Parallel to `inputs`: remembers each tile's natural cell size so
    // the atlas result carries it back out to the frontend.
    let mut nat_by_name: std::collections::HashMap<String, (u32, u32)> =
        std::collections::HashMap::new();
    for name in &names {
        let rendered = render_tile_image(
            name,
            &all_loaders,
            &priority,
            extract_dir.as_ref(),
            &mut sheet_cache,
        );
        nat_by_name.insert(name.clone(), (rendered.nat_w_cells, rendered.nat_h_cells));
        inputs.push(TileInput {
            name: name.clone(),
            image: rendered.image,
        });
    }
    let atlas = build_atlas(inputs, AtlasOptions::default()).map_err(|e| e.to_string())?;
    let tiles = atlas
        .tiles
        .into_iter()
        .map(|(name, uv)| {
            let (nw, nh) = nat_by_name.get(&name).copied().unwrap_or((1, 1));
            let (ax, ay) = anchor_for_tile(&name, nw, nh);
            EditorAtlasTile {
                name,
                x: uv.x,
                y: uv.y,
                w: uv.w,
                h: uv.h,
                nat_w_cells: nw,
                nat_h_cells: nh,
                anchor_x_cells: ax,
                anchor_y_cells: ay,
            }
        })
        .collect();

    let mut png_data_url = String::from("data:image/png;base64,");
    STANDARD.encode_string(&atlas.png, &mut png_data_url);

    Ok(EditorAtlas {
        png_data_url,
        width: atlas.width,
        height: atlas.height,
        tile_size: 64,
        tiles,
    })
}

fn color_for_name(name: &str) -> [u8; 3] {
    // FNV-1a 32-bit for stability across runs.
    let mut hash: u32 = 0x811C9DC5;
    for b in name.as_bytes() {
        hash ^= *b as u32;
        hash = hash.wrapping_mul(0x01000193);
    }
    let r = 60 + ((hash & 0xFF) as u8 / 2);
    let g = 60 + (((hash >> 8) & 0xFF) as u8 / 2);
    let b = 60 + (((hash >> 16) & 0xFF) as u8 / 2);
    [r, g, b]
}

/// Text color that reads against `bg`. White on dark, black on light,
/// using 299/587/114 luminance weighting.
fn text_color_for_bg(bg: [u8; 3]) -> [u8; 4] {
    let lum = bg[0] as f32 * 0.299 + bg[1] as f32 * 0.587 + bg[2] as f32 * 0.114;
    if lum > 160.0 {
        [0, 0, 0, 255]
    } else {
        [255, 255, 255, 255]
    }
}

/// FiraSans-SemiBold, bundled at compile time. Used for the missing-
/// tile placeholder label so text renders identically regardless of the
/// host system's installed fonts.
const PLACEHOLDER_FONT_BYTES: &[u8] = include_bytes!("../resources/fonts/FiraSans-SemiBold.ttf");

fn placeholder_font() -> &'static ab_glyph::FontRef<'static> {
    use ab_glyph::FontRef;
    use std::sync::OnceLock;
    static FONT: OnceLock<FontRef<'static>> = OnceLock::new();
    FONT.get_or_init(|| {
        FontRef::try_from_slice(PLACEHOLDER_FONT_BYTES)
            .expect("bundled FiraSans-SemiBold.ttf must parse")
    })
}

/// Stamps the tile name onto the placeholder:
///   - split the name on `_` into lines (`lunar_floor_jungle` -> three
///     lines, one word each)
///   - grow the font size until either dimension no longer fits within
///     an inner rect (width - 2*pad, height - 3*pad)
///   - center the whole block; draw with a luminance-aware text color
///
/// Text is opaque so it stays legible when the atlas gets upscaled on
/// the frontend canvas.
fn stamp_name_label(img: &mut image::RgbaImage, name: &str) {
    let w = img.width() as f32;
    let h = img.height() as f32;
    // Small edge padding so glyphs never touch the tile border. Kept
    // tight because the fit metric below already uses glyph-tight
    // heights (ascent - descent, no line gap), so no additional slack
    // for font leading is needed.
    let pad_x = 2.0;
    let pad_y = 2.0;
    let inner_w = w - 2.0 * pad_x;
    let inner_h = h - 2.0 * pad_y;
    if inner_w <= 0.0 || inner_h <= 0.0 {
        return;
    }

    let bg = {
        let p = img.get_pixel(0, 0);
        [p[0], p[1], p[2]]
    };
    let fg = text_color_for_bg(bg);

    let lines: Vec<&str> = name.split('_').filter(|s| !s.is_empty()).collect();
    let lines: Vec<&str> = if lines.is_empty() { vec![name] } else { lines };
    let font = placeholder_font();

    // Grow the font size until the tightest bounding box of the text
    // block would overflow the inner rect. Tight-fit metric:
    //   line_h = ascent - descent   (no leading, no line gap)
    // The fit result actually fills the tile instead of leaving
    // 15-25% padding for the font's built-in leading.
    use ab_glyph::{Font, PxScale, ScaleFont};
    let max_size = h.max(64.0) as u32;
    let mut best_size = 4.0f32;
    for size in (4..=max_size).rev() {
        let scale = PxScale::from(size as f32);
        let scaled = font.as_scaled(scale);
        let line_h = scaled.ascent() - scaled.descent();
        let block_h = line_h * lines.len() as f32;
        if block_h > inner_h {
            continue;
        }
        let max_w = lines
            .iter()
            .map(|line| line_width(&scaled, line))
            .fold(0.0f32, f32::max);
        if max_w > inner_w {
            continue;
        }
        best_size = size as f32;
        break;
    }

    let scale = PxScale::from(best_size);
    let scaled = font.as_scaled(scale);
    let line_h = scaled.ascent() - scaled.descent();
    let block_h = line_h * lines.len() as f32;
    let start_y = (h - block_h) * 0.5;

    for (i, line) in lines.iter().enumerate() {
        let line_w = line_width(&scaled, line);
        let mut caret_x = (w - line_w) * 0.5;
        let baseline_y = start_y + line_h * i as f32 + scaled.ascent();
        for ch in line.chars() {
            let glyph_id = font.glyph_id(ch);
            let glyph =
                glyph_id.with_scale_and_position(scale, ab_glyph::point(caret_x, baseline_y));
            if let Some(outlined) = font.outline_glyph(glyph) {
                let bounds = outlined.px_bounds();
                outlined.draw(|gx, gy, coverage| {
                    let px = (bounds.min.x + gx as f32).round() as i32;
                    let py = (bounds.min.y + gy as f32).round() as i32;
                    if px < 0 || py < 0 || (px as u32) >= img.width() || (py as u32) >= img.height()
                    {
                        return;
                    }
                    let alpha = (coverage * fg[3] as f32).round().clamp(0.0, 255.0) as u8;
                    if alpha == 0 {
                        return;
                    }
                    blend_pixel(img, px as u32, py as u32, [fg[0], fg[1], fg[2], alpha]);
                });
            }
            caret_x += scaled.h_advance(glyph_id);
        }
    }
}

fn line_width<F, SF>(scaled: &SF, line: &str) -> f32
where
    F: ab_glyph::Font,
    SF: ab_glyph::ScaleFont<F>,
{
    let mut w = 0.0;
    for ch in line.chars() {
        let id = scaled.font().glyph_id(ch);
        w += scaled.h_advance(id);
    }
    w
}

fn blend_pixel(img: &mut image::RgbaImage, x: u32, y: u32, over: [u8; 4]) {
    let under = img.get_pixel(x, y).0;
    let a = over[3] as f32 / 255.0;
    let inv = 1.0 - a;
    let out = [
        (over[0] as f32 * a + under[0] as f32 * inv).round() as u8,
        (over[1] as f32 * a + under[1] as f32 * inv).round() as u8,
        (over[2] as f32 * a + under[2] as f32 * inv).round() as u8,
        255,
    ];
    img.put_pixel(x, y, image::Rgba(out));
}

/// 5-row bitmap per glyph, 3 bits wide (LSB = rightmost pixel).
fn glyph_pattern(ch: char) -> [u8; 5] {
    match ch {
        'a' => [0b010, 0b101, 0b111, 0b101, 0b101],
        'b' => [0b110, 0b101, 0b110, 0b101, 0b110],
        'c' => [0b011, 0b100, 0b100, 0b100, 0b011],
        'd' => [0b110, 0b101, 0b101, 0b101, 0b110],
        'e' => [0b111, 0b100, 0b110, 0b100, 0b111],
        'f' => [0b111, 0b100, 0b110, 0b100, 0b100],
        'g' => [0b011, 0b100, 0b101, 0b101, 0b011],
        'h' => [0b101, 0b101, 0b111, 0b101, 0b101],
        'i' => [0b111, 0b010, 0b010, 0b010, 0b111],
        'j' => [0b001, 0b001, 0b001, 0b101, 0b010],
        'k' => [0b101, 0b110, 0b100, 0b110, 0b101],
        'l' => [0b100, 0b100, 0b100, 0b100, 0b111],
        'm' => [0b101, 0b111, 0b111, 0b101, 0b101],
        'n' => [0b101, 0b111, 0b111, 0b111, 0b101],
        'o' => [0b010, 0b101, 0b101, 0b101, 0b010],
        'p' => [0b110, 0b101, 0b110, 0b100, 0b100],
        'q' => [0b010, 0b101, 0b101, 0b111, 0b011],
        'r' => [0b110, 0b101, 0b110, 0b110, 0b101],
        's' => [0b011, 0b100, 0b010, 0b001, 0b110],
        't' => [0b111, 0b010, 0b010, 0b010, 0b010],
        'u' => [0b101, 0b101, 0b101, 0b101, 0b010],
        'v' => [0b101, 0b101, 0b101, 0b010, 0b010],
        'w' => [0b101, 0b101, 0b111, 0b111, 0b101],
        'x' => [0b101, 0b101, 0b010, 0b101, 0b101],
        'y' => [0b101, 0b101, 0b010, 0b010, 0b010],
        'z' => [0b111, 0b001, 0b010, 0b100, 0b111],
        '0' => [0b010, 0b101, 0b101, 0b101, 0b010],
        '1' => [0b010, 0b110, 0b010, 0b010, 0b111],
        '2' => [0b110, 0b001, 0b010, 0b100, 0b111],
        '3' => [0b110, 0b001, 0b010, 0b001, 0b110],
        '4' => [0b101, 0b101, 0b111, 0b001, 0b001],
        '5' => [0b111, 0b100, 0b110, 0b001, 0b110],
        '6' => [0b011, 0b100, 0b110, 0b101, 0b010],
        '7' => [0b111, 0b001, 0b010, 0b010, 0b010],
        '8' => [0b010, 0b101, 0b010, 0b101, 0b010],
        '9' => [0b010, 0b101, 0b011, 0b001, 0b110],
        '_' => [0b000, 0b000, 0b000, 0b000, 0b111],
        _ => [0b111, 0b101, 0b101, 0b101, 0b111], // unknown box
    }
}

// ---- Vanilla level loading + save (phase 7.4) -------------------------------

fn extracts_levels_dir() -> Result<PathBuf, String> {
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    Ok(install_dir
        .join("Mods")
        .join("Extracted")
        .join("Data")
        .join("Levels"))
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum VanillaLevelSource {
    /// File exists only in the vanilla extracts, not in the pack yet.
    Vanilla,
    /// The pack has already overridden the vanilla file.
    Modded,
    /// The pack ships this `.lvl` but it isn't a base-game file -- an
    /// extra level the author added. Editable here, but it has no vanilla
    /// original to fall back to. Surfaced with a distinct (red) icon so
    /// authors can tell it apart from base-game files.
    Custom,
}

/// The hardcoded sister-group list. Each inner group is a set of files
/// that load together in-game and therefore share a tilecode namespace.
const SISTER_GROUPS: &[&[&str]] = &[
    &[
        "basecamp.lvl",
        "basecamp_garden.lvl",
        "basecamp_shortcut_discovered.lvl",
        "basecamp_shortcut_undiscovered.lvl",
        "basecamp_shortcut_unlocked.lvl",
        "basecamp_surface.lvl",
        "basecamp_tutorial.lvl",
        "basecamp_tv_room_locked.lvl",
        "basecamp_tv_room_unlocked.lvl",
    ],
    &["junglearea.lvl", "blackmarket.lvl", "beehive.lvl"],
    &["junglearea.lvl", "challenge_moon.lvl", "beehive.lvl"],
    &["volcanoarea.lvl", "vladscastle.lvl"],
    &["volcanoarea.lvl", "challenge_moon.lvl"],
    &["tidepoolarea.lvl", "challenge_star.lvl", "lake.lvl"],
    &["tidepoolarea.lvl", "lakeoffire.lvl"],
    &["templearea.lvl", "challenge_star.lvl", "beehive.lvl"],
    &["babylonarea.lvl", "babylonarea_1-1.lvl"],
    &["babylonarea.lvl", "hallofushabti.lvl"],
    &["babylonarea.lvl", "palaceofpleasure.lvl"],
    &["sunkencityarea.lvl", "challenge_sun.lvl"],
    &["ending.lvl", "ending_hard.lvl"],
];

/// The list of files that inherit from `generic.lvl`. Used when
/// editing generic.lvl itself to know which files' tilecodes must not
/// collide.
const GENERIC_DEPENDENTS: &[&str] = &[
    "dwellingarea.lvl",
    "cavebossarea.lvl",
    "junglearea.lvl",
    "blackmarket.lvl",
    "beehive.lvl",
    "challenge_moon.lvl",
    "volcanoarea.lvl",
    "vladscastle.lvl",
    "olmecarea.lvl",
    "tidepoolarea.lvl",
    "lake.lvl",
    "lakeoffire.lvl",
    "challenge_star.lvl",
    "abzu.lvl",
    "templearea.lvl",
    "cityofgold.lvl",
    "duat.lvl",
    "icecavesarea.lvl",
    "babylonarea.lvl",
    "babylonarea_1-1.lvl",
    "hallofushabti.lvl",
    "palaceofpleasure.lvl",
    "tiamat.lvl",
    "sunkencityarea.lvl",
    "challenge_sun.lvl",
    "eggplantarea.lvl",
    "hundun.lvl",
    "ending.lvl",
    "ending_hard.lvl",
    "cosmicocean_babylon.lvl",
    "cosmicocean_dwelling.lvl",
    "cosmicocean_icecavesarea.lvl",
    "cosmicocean_jungle.lvl",
    "cosmicocean_sunkencity.lvl",
    "cosmicocean_temple.lvl",
    "cosmicocean_tidepool.lvl",
    "cosmicocean_volcano.lvl",
];

/// Every sister-location file for `file_name`, deduped and excluding
/// the file itself. Returned as a flat list because the UI only needs
/// "what other files share this tilecode namespace", not the grouped
/// structure.
fn sister_files_for(file_name: &str) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut seen: std::collections::HashSet<String> = Default::default();
    let push = |name: &str, out: &mut Vec<String>, seen: &mut std::collections::HashSet<String>| {
        if name == file_name {
            return;
        }
        if seen.insert(name.to_string()) {
            out.push(name.to_string());
        }
    };

    if file_name == "generic.lvl" {
        // Editing generic.lvl itself: its "sisters" are every file
        // that includes it, since a code assigned here must not
        // collide with any of them.
        for dep in GENERIC_DEPENDENTS {
            push(dep, &mut out, &mut seen);
        }
        return out;
    }

    let mut matched_any_group = false;
    for group in SISTER_GROUPS {
        if group.contains(&file_name) {
            matched_any_group = true;
            for f in *group {
                push(f, &mut out, &mut seen);
            }
        }
    }

    // Everything except basecamp inherits from generic.lvl.
    let is_basecamp = file_name.starts_with("basecamp");
    if !is_basecamp {
        push("generic.lvl", &mut out, &mut seen);
    }

    // Files not in any sister group still get generic.lvl (already added
    // above) and nothing else. If matched_any_group is false and file is
    // basecamp, there are simply no sisters.
    let _ = matched_any_group;
    out
}

/// Codes that `generic.lvl`'s rooms reference but no file actually declares;
/// the game hardcodes these bindings. Every generic-inheriting file needs them
/// to render rooms that use these codes (e.g. `=` minewood floor in an area
/// setroom), so they seed the render map as its lowest-precedence layer.
const GENERIC_IMPLICIT: &[(char, &str)] = &[
    ('4', "push_block"),
    ('t', "treasure"),
    ('1', "floor"),
    ('6', "chunk_air"),
    ('=', "minewood_floor"),
];

/// The parent files whose tile codes a level *inherits* for rendering,
/// in lowest-to-highest precedence order (a later parent's binding for a
/// given code overrides an earlier one, and the file's own codes override
/// all of these). Mirrors the Python editor's `dependencies_for_level`:
/// every non-basecamp file inherits `generic.lvl`, and a handful of
/// sub-locations also inherit their host area file (e.g. `blackmarket`
/// inherits `junglearea`). Without this, a room that uses a code declared
/// only in a parent (very common: olmecarea's setrooms use `generic`'s wood
/// tiles) renders those cells blank.
///
/// Distinct from `sister_files_for`, which is the broader collision set used
/// for the palette panel; this is strictly the render-inheritance chain.
fn render_dependencies_for(file_name: &str) -> Vec<&'static str> {
    let l = file_name.to_ascii_lowercase();
    if l.starts_with("base") {
        return vec!["basecamp.lvl"];
    }
    // generic.lvl is the universal base; parents listed after it win ties.
    let mut deps = vec!["generic.lvl"];
    if l.starts_with("blackmark") {
        deps.push("junglearea.lvl");
    } else if l.starts_with("beehive") {
        deps.push("templearea.lvl");
        deps.push("junglearea.lvl");
    } else if l.starts_with("vlads") {
        deps.push("volcanoarea.lvl");
    } else if l.starts_with("challenge_moon") {
        deps.push("junglearea.lvl");
        deps.push("volcanoarea.lvl");
    } else if l.starts_with("lake") {
        deps.push("tidepoolarea.lvl");
    } else if l.starts_with("challenge_star") {
        deps.push("tidepoolarea.lvl");
        deps.push("templearea.lvl");
    } else if l.starts_with("hallofush")
        || l.starts_with("babylonarea_1")
        || l.starts_with("palace")
    {
        deps.push("babylonarea.lvl");
    } else if l.starts_with("challenge_sun") {
        deps.push("sunkencityarea.lvl");
    } else if l.starts_with("end") {
        deps.push("ending.lvl");
    }
    deps
}

/// Resolves a sister-location file to the pack copy if present, else
/// the vanilla extract. Returns None if neither exists (fine for the
/// dependency load path, the caller just skips that sister).
fn resolve_sister_path(pack: &str, file_name: &str) -> Option<PathBuf> {
    let sanitized = validate_pack_name(pack).ok()?;
    let pack_path = packs_dir()
        .ok()?
        .join(&sanitized)
        .join("Data")
        .join("Levels")
        .join(file_name);
    if pack_path.exists() {
        return Some(pack_path);
    }
    let extract_path = extracts_levels_dir().ok()?.join(file_name);
    if extract_path.exists() {
        return Some(extract_path);
    }
    None
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DependencyPalette {
    /// The sister-location file name, e.g. "junglearea.lvl". Displayed as
    /// a section header in the palette panel.
    pub file_name: String,
    /// Whether this sister came from the pack (Modded) or extracts
    /// (Vanilla). Used to hint the source in the UI.
    pub source: VanillaLevelSource,
    /// The sister's tile-code entries. Same shape as the current file's
    /// palette so the frontend can render them with the same swatch code.
    pub palette: Vec<CustomLevelPaletteEntry>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VanillaLevelListEntry {
    pub file_name: String,
    pub source: VanillaLevelSource,
}

/// Lists vanilla `.lvl` files as they appear to this pack: everything in the
/// extract dir, tagged Modded if the pack overrides it. Files in the pack
/// that aren't in extracts fall out of this list (those are custom levels).
///
/// Comparison is case-insensitive so Windows filesystems (where the pack
/// might have `DwellingArea.lvl` and extracts have `dwellingarea.lvl`) still
/// match up.
#[tauri::command]
pub fn list_vanilla_levels(pack: String) -> Result<Vec<VanillaLevelListEntry>, String> {
    let sanitized = validate_pack_name(&pack)?;
    let extracts = extracts_levels_dir()?;
    if !extracts.exists() {
        return Err(format!(
            "extracted levels not found at {}; run Extract Assets first",
            extracts.display()
        ));
    }
    let pack_levels = packs_dir()?.join(&sanitized).join("Data").join("Levels");

    let mut vanilla_names: std::collections::BTreeMap<String, String> = Default::default();
    let mut arena_names: std::collections::BTreeMap<String, String> = Default::default();
    collect_lvls(&extracts, &mut vanilla_names, &mut arena_names)?;

    // The pack's own .lvl files. Keyed lowercase like the vanilla maps so
    // membership tests are case-insensitive.
    let mut pack_top: std::collections::BTreeMap<String, String> = Default::default();
    let mut pack_arena: std::collections::BTreeMap<String, String> = Default::default();
    if pack_levels.exists() {
        collect_lvls(&pack_levels, &mut pack_top, &mut pack_arena)?;
    }

    let mut out = Vec::new();
    for (key, original) in &vanilla_names {
        let source = if pack_top.contains_key(key) {
            VanillaLevelSource::Modded
        } else {
            VanillaLevelSource::Vanilla
        };
        out.push(VanillaLevelListEntry {
            file_name: original.clone(),
            source,
        });
    }
    for (key, original) in &arena_names {
        let source = if pack_arena.contains_key(key) {
            VanillaLevelSource::Modded
        } else {
            VanillaLevelSource::Vanilla
        };
        out.push(VanillaLevelListEntry {
            file_name: format!("Arena/{original}"),
            source,
        });
    }
    // Pack-shipped .lvl files that don't correspond to any base-game file.
    // These have no vanilla original; the old editor surfaced them (red
    // icon) so authors could still view/edit extra levels living in the
    // pack. A file whose key IS in the vanilla set is an override and was
    // already emitted as Modded above.
    for (key, original) in &pack_top {
        if !vanilla_names.contains_key(key) {
            out.push(VanillaLevelListEntry {
                file_name: original.clone(),
                source: VanillaLevelSource::Custom,
            });
        }
    }
    for (key, original) in &pack_arena {
        if !arena_names.contains_key(key) {
            out.push(VanillaLevelListEntry {
                file_name: format!("Arena/{original}"),
                source: VanillaLevelSource::Custom,
            });
        }
    }
    out.sort_by_key(|a| a.file_name.to_lowercase());
    Ok(out)
}

/// Scans `dir` for `*.lvl` files (immediate children only) and its
/// `Arena/` subdirectory. Returns lowercase filename as the map KEY so
/// case-insensitive comparisons work, and preserves the original filename
/// as the VALUE for display.
fn collect_lvls(
    dir: &std::path::Path,
    top: &mut std::collections::BTreeMap<String, String>,
    arena: &mut std::collections::BTreeMap<String, String>,
) -> Result<(), String> {
    for entry in std::fs::read_dir(dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let ft = entry.file_type().map_err(|e| e.to_string())?;
        let name_os = entry.file_name();
        let Some(name) = name_os.to_str() else {
            continue;
        };
        if ft.is_file() && name.to_lowercase().ends_with(".lvl") {
            top.insert(name.to_lowercase(), name.to_string());
        } else if ft.is_dir() && name.eq_ignore_ascii_case("Arena") {
            for ae in std::fs::read_dir(entry.path()).map_err(|e| e.to_string())? {
                let ae = ae.map_err(|e| e.to_string())?;
                if !ae.file_type().map(|t| t.is_file()).unwrap_or(false) {
                    continue;
                }
                if let Some(n) = ae.file_name().to_str()
                    && n.to_lowercase().ends_with(".lvl")
                {
                    arena.insert(n.to_lowercase(), n.to_string());
                }
            }
        }
    }
    Ok(())
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VanillaRoom {
    pub settings: Vec<String>,
    pub foreground: Vec<Vec<String>>,
    pub background: Vec<Vec<String>>,
    pub width: u32,
    pub height: u32,
    pub comment: Option<String>,
    /// True if any of the settings is `dual` or the room actually has a
    /// non-empty background layer. Used by the frontend to show/hide the
    /// background-layer toggle.
    pub is_dual: bool,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VanillaTemplate {
    pub name: String,
    pub comment: Option<String>,
    pub rooms: Vec<VanillaRoom>,
}

/// A rules row for the Rules panel. Value is always stringified so the UI
/// can render one input regardless of the underlying type; the backend
/// re-parses it via ml2_levels' existing line parsers on save.
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RulesEntry {
    pub name: String,
    pub value: String,
    #[serde(default)]
    pub comment: Option<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VanillaLevelData {
    pub file_name: String,
    pub source: VanillaLevelSource,
    pub templates: Vec<VanillaTemplate>,
    pub palette: Vec<CustomLevelPaletteEntry>,
    pub level_settings: Vec<RulesEntry>,
    pub level_chances: Vec<RulesEntry>,
    pub monster_chances: Vec<RulesEntry>,
    /// Every sister-location file's palette. Frontend renders these as
    /// separate labeled sections below the main palette so authors can
    /// see (and adopt) tiles inherited from parent files. Also feeds the
    /// collision-aware code allocation.
    pub dependency_palettes: Vec<DependencyPalette>,
    /// Theme id from the file's tool-owned comment marker, if present. Lets
    /// the vanilla editor honor an author-set theme instead of guessing from
    /// the filename. `None` -> the frontend falls back to `biomeForLevelFilename`.
    pub detected_theme: Option<i32>,
    /// Subtheme id from the same marker (only meaningful for Cosmic Ocean).
    pub detected_subtheme: Option<i32>,
}

// --- Vanilla per-file theme marker ------------------------------------------
//
// The vanilla editor normally guesses a level's biome from its filename
// (`biomeForLevelFilename`). Custom (pack-only) files have arbitrary names, so
// there's nothing to guess from. Rather than reuse a template comment (which
// authors edit freely) or a sidecar file, we stash an explicit theme in the
// level's TOP comment banner -- `LevelFile.comment`, the one comment the
// format round-trips separately from template/section comments. The marker is
// a single tool-owned line the game ignores:
//
//     // ------------------------------
//     // modlunky2: theme=jungle subtheme=abzu
//
// Storage rules that keep this robust:
//   * We match on the `modlunky2:` content token, NOT an exact `//` prefix,
//     because `format_comment` normalizes each line's leading slashes on write.
//   * The block is fenced with the exact `SECTION_COMMENT` dash banner, since
//     the parser only captures `file.comment` when the block starts with it.
//   * Reset (theme = None) strips only our line and, if no human banner text
//     remains, drops the whole banner so the file keeps zero trace of it.

/// Theme id <-> stable slug for the file-comment marker. Ids match
/// `LevelConfigPanel.THEMES` on the frontend and `biomeForThemeId`. Slugs are
/// lowercase and punctuation-free so they survive comment normalization.
const THEME_SLUGS: &[(i32, &str)] = &[
    (1, "dwelling"),
    (2, "jungle"),
    (3, "volcana"),
    (4, "olmec"),
    (5, "tidepool"),
    (6, "temple"),
    (7, "icecaves"),
    (8, "neobabylon"),
    (9, "sunkencity"),
    (10, "cosmicocean"),
    (11, "cityofgold"),
    (12, "duat"),
    (13, "abzu"),
    (14, "tiamat"),
    (15, "eggplant"),
    (16, "hundun"),
    (17, "basecamp"),
];

/// Content token that identifies our tool-owned config line.
const THEME_MARKER_TOKEN: &str = "modlunky2:";

fn theme_slug(id: i32) -> Option<&'static str> {
    THEME_SLUGS.iter().find(|(i, _)| *i == id).map(|(_, s)| *s)
}

fn theme_id_from_slug(slug: &str) -> Option<i32> {
    let slug = slug.trim().to_ascii_lowercase();
    THEME_SLUGS
        .iter()
        .find(|(_, s)| *s == slug)
        .map(|(i, _)| *i)
}

/// Strip a comment line's decorative leading `/`, `!`, and spaces, leaving
/// the bare content (e.g. `// modlunky2: theme=x` -> `modlunky2: theme=x`).
fn comment_line_body(line: &str) -> &str {
    line.trim_start_matches(['/', ' ', '!']).trim()
}

fn is_theme_marker_line(line: &str) -> bool {
    comment_line_body(line)
        .to_ascii_lowercase()
        .starts_with(THEME_MARKER_TOKEN)
}

/// A dash banner (`// ------...`) used to fence comment blocks. Purely
/// structural; carries no author content.
fn is_dash_banner(line: &str) -> bool {
    let body = comment_line_body(line);
    !body.is_empty() && body.chars().all(|c| c == '-')
}

/// Parses (theme, subtheme) ids out of a level file's top comment. Either is
/// `None` when absent or unrecognized.
fn parse_theme_marker(comment: Option<&str>) -> (Option<i32>, Option<i32>) {
    let Some(comment) = comment else {
        return (None, None);
    };
    for line in comment.lines() {
        if !is_theme_marker_line(line) {
            continue;
        }
        let body = comment_line_body(line);
        let rest = &body[THEME_MARKER_TOKEN.len()..];
        let mut theme = None;
        let mut subtheme = None;
        for tok in rest.split_whitespace() {
            if let Some(v) = tok.strip_prefix("theme=") {
                theme = theme_id_from_slug(v);
            } else if let Some(v) = tok.strip_prefix("subtheme=") {
                subtheme = theme_id_from_slug(v);
            }
        }
        return (theme, subtheme);
    }
    (None, None)
}

/// Rebuilds a level file's top comment with the theme marker inserted,
/// updated, or (when `theme` is `None`) removed. Preserves any human banner
/// text. Returns `None` when the banner would be empty so nothing gets
/// written -- a reset leaves the file with no marker at all.
fn upsert_theme_marker(
    existing: Option<&str>,
    theme: Option<i32>,
    subtheme: Option<i32>,
) -> Option<String> {
    // Keep author banner lines; drop our marker + structural noise (blank
    // lines and dash banners, which we re-fence ourselves).
    let mut human: Vec<String> = Vec::new();
    if let Some(existing) = existing {
        for line in existing.lines() {
            if is_theme_marker_line(line) || line.trim().is_empty() || is_dash_banner(line) {
                continue;
            }
            human.push(comment_line_body(line).to_string());
        }
    }

    let marker_line = theme.and_then(theme_slug).map(|slug| {
        let mut line = format!("// {THEME_MARKER_TOKEN} theme={slug}");
        if let Some(sub_slug) = subtheme.and_then(theme_slug) {
            line.push_str(&format!(" subtheme={sub_slug}"));
        }
        line
    });

    // Nothing tool-owned and no author text -> drop the banner entirely.
    if marker_line.is_none() && human.is_empty() {
        return None;
    }

    // Open with the exact SECTION_COMMENT so the parser re-captures this as
    // file.comment on the next load.
    let mut out = format!("{SECTION_COMMENT}\n");
    for h in &human {
        out.push_str(&format!("// {h}\n"));
    }
    if let Some(marker) = marker_line {
        out.push_str(&marker);
        out.push('\n');
    }
    Some(out)
}

fn resolve_vanilla_level_path(
    pack: &str,
    file_name: &str,
) -> Result<(PathBuf, VanillaLevelSource), String> {
    let sanitized = validate_pack_name(pack)?;
    if file_name.contains("..") || file_name.starts_with('/') || file_name.starts_with('\\') {
        return Err(format!("invalid level file: {file_name:?}"));
    }
    let pack_path = packs_dir()?
        .join(&sanitized)
        .join("Data")
        .join("Levels")
        .join(file_name);
    if pack_path.exists() {
        return Ok((pack_path, VanillaLevelSource::Modded));
    }
    let extract_path = extracts_levels_dir()?.join(file_name);
    if extract_path.exists() {
        return Ok((extract_path, VanillaLevelSource::Vanilla));
    }
    Err(format!(
        "level not found: {} (looked in pack and extracts)",
        file_name
    ))
}

/// Loads a vanilla `.lvl` file. Prefers the pack's copy if it exists, else
/// falls back to the extracted vanilla file so the user can start editing
/// from vanilla state. All templates + rooms + settings + tile codes come
/// back so the frontend can render any room the user picks.
#[tauri::command]
pub async fn load_vanilla_level(
    pack: String,
    file_name: String,
) -> Result<VanillaLevelData, String> {
    let (path, source) = resolve_vanilla_level_path(&pack, &file_name)?;
    let pack_for_deps = pack.clone();
    tauri::async_runtime::spawn_blocking(move || {
        load_vanilla_level_sync(pack_for_deps, file_name, path, source)
    })
    .await
    .map_err(|e| format!("load task panicked: {e}"))?
}

fn load_vanilla_level_sync(
    pack: String,
    file_name: String,
    path: PathBuf,
    source: VanillaLevelSource,
) -> Result<VanillaLevelData, String> {
    let level = LevelFile::from_path(&path).map_err(|e| e.to_string())?;

    // char -> tile-code name lookup. Seed it from the file's render-inheritance
    // chain (generic.lvl and any host-area parents) so codes a room uses but
    // this file doesn't itself declare still resolve to a sprite. Parents are
    // applied in precedence order; the file's own codes below overwrite them.
    // Only `code_to_name` is seeded -- `palette` stays the file's own codes, so
    // inherited bindings render without polluting the editable palette (the
    // parents' full palettes surface separately via `dependency_palettes`).
    let mut code_to_name: std::collections::HashMap<char, String> =
        std::collections::HashMap::new();
    // Lowest layer: the hardcoded generic bindings, for any file that inherits
    // generic.lvl (everything but basecamp). A real declaration below overrides.
    if !file_name.to_ascii_lowercase().starts_with("base") {
        for (ch, name) in GENERIC_IMPLICIT {
            code_to_name.insert(*ch, (*name).to_string());
        }
    }
    for dep in render_dependencies_for(&file_name) {
        let Some(dep_path) = resolve_sister_path(&pack, dep) else {
            continue;
        };
        let Ok(dep_level) = LevelFile::from_path(&dep_path) else {
            continue;
        };
        for tc in dep_level.tile_codes.all() {
            if let Some(ch) = tc.value.chars().next() {
                code_to_name.insert(ch, tc.name.clone());
            }
        }
    }

    let mut palette = Vec::new();
    for tc in level.tile_codes.all() {
        if let Some(ch) = tc.value.chars().next() {
            code_to_name.insert(ch, tc.name.clone());
        }
        palette.push(CustomLevelPaletteEntry {
            name: tc.name.clone(),
            code: tc.value.clone(),
            comment: tc.comment.clone(),
        });
    }

    // When editing generic.lvl itself, also surface the hardcoded implicit
    // codes in the editable palette (not just the render map) so the author can
    // see and paint them. Skip any binding whose code or name is already declared.
    if file_name.starts_with("generic") {
        let mut used_names: std::collections::HashSet<String> =
            palette.iter().map(|p| p.name.clone()).collect();
        for (ch, name) in GENERIC_IMPLICIT {
            if code_to_name.contains_key(ch) || used_names.contains(*name) {
                continue;
            }
            code_to_name.insert(*ch, (*name).to_string());
            used_names.insert((*name).to_string());
            palette.push(CustomLevelPaletteEntry {
                name: (*name).to_string(),
                code: ch.to_string(),
                comment: None,
            });
        }
    }

    let mut templates = Vec::new();
    for tpl in level.level_templates.all() {
        let mut rooms = Vec::new();
        for r in &tpl.rooms {
            let is_dual = !r.background.is_empty()
                || r.settings
                    .iter()
                    .any(|s| matches!(s, ml2_levels::TemplateSetting::Dual));
            let width = r
                .foreground
                .first()
                .map(|row| row.len() as u32)
                .unwrap_or(0);
            let height = r.foreground.len() as u32;
            rooms.push(VanillaRoom {
                settings: r.settings.iter().map(|s| s.as_str().to_string()).collect(),
                foreground: r
                    .foreground
                    .iter()
                    .map(|row| {
                        row.iter()
                            .map(|ch| code_to_name.get(ch).cloned().unwrap_or_default())
                            .collect()
                    })
                    .collect(),
                background: r
                    .background
                    .iter()
                    .map(|row| {
                        row.iter()
                            .map(|ch| code_to_name.get(ch).cloned().unwrap_or_default())
                            .collect()
                    })
                    .collect(),
                width,
                height,
                comment: r.comment.clone(),
                is_dual,
            });
        }
        templates.push(VanillaTemplate {
            name: tpl.name.clone(),
            comment: tpl.comment.clone(),
            rooms,
        });
    }

    let level_settings = level
        .level_settings
        .all()
        .map(|s| RulesEntry {
            name: s.name.clone(),
            value: level_setting_value_to_str(&s.value),
            comment: s.comment.clone(),
        })
        .collect();
    let level_chances = level
        .level_chances
        .all()
        .map(|c| RulesEntry {
            name: c.name.clone(),
            value: chance_value_to_str(&c.value),
            comment: c.comment.clone(),
        })
        .collect();
    let monster_chances = level
        .monster_chances
        .all()
        .map(|c| RulesEntry {
            name: c.name.clone(),
            value: chance_value_to_str(&c.value),
            comment: c.comment.clone(),
        })
        .collect();

    let dependency_palettes = build_dependency_palettes(&pack, &file_name);
    let (detected_theme, detected_subtheme) = parse_theme_marker(level.comment.as_deref());

    Ok(VanillaLevelData {
        file_name,
        source,
        templates,
        palette,
        level_settings,
        level_chances,
        monster_chances,
        dependency_palettes,
        detected_theme,
        detected_subtheme,
    })
}

/// Walks every sister-location file for `file_name`, loads it, and returns
/// each one's tilecode palette. Sisters that don't exist on disk (neither
/// in the pack nor in extracts) are silently skipped, and unreadable files
/// are also skipped so a broken sister doesn't take down the whole editor.
fn build_dependency_palettes(pack: &str, file_name: &str) -> Vec<DependencyPalette> {
    let mut out = Vec::new();
    for sister in sister_files_for(file_name) {
        let Some(sister_path) = resolve_sister_path(pack, &sister) else {
            continue;
        };
        // Was this sister modded by the pack, or is it a vanilla extract?
        // Cheap check: does the pack copy exist?
        let source = if validate_pack_name(pack)
            .ok()
            .and_then(|s| packs_dir().ok().map(|d| d.join(s)))
            .map(|d| d.join("Data").join("Levels").join(&sister).exists())
            .unwrap_or(false)
        {
            VanillaLevelSource::Modded
        } else {
            VanillaLevelSource::Vanilla
        };
        let Ok(level) = LevelFile::from_path(&sister_path) else {
            continue;
        };
        let palette: Vec<CustomLevelPaletteEntry> = level
            .tile_codes
            .all()
            .map(|tc| CustomLevelPaletteEntry {
                name: tc.name.clone(),
                code: tc.value.clone(),
                comment: tc.comment.clone(),
            })
            .collect();
        out.push(DependencyPalette {
            file_name: sister,
            source,
            palette,
        });
    }
    out
}

fn level_setting_value_to_str(v: &LevelSettingValue) -> String {
    match v {
        LevelSettingValue::Int(x) => x.to_string(),
        // Debug format matches ml2_levels' own writer: always include a
        // decimal point on floats (`10.0`, not `10`).
        LevelSettingValue::Float(x) => format!("{:?}", x),
        LevelSettingValue::Size(w, h) => format!("{w} {h}"),
    }
}

fn chance_value_to_str(v: &ChanceValue) -> String {
    match v {
        ChanceValue::Single(x) => x.to_string(),
        ChanceValue::PerDifficulty(vs) => {
            vs.iter().map(i64::to_string).collect::<Vec<_>>().join(", ")
        }
    }
}

/// Rules edits sent from the frontend. Any of the three fields being
/// `Some(...)` replaces the on-disk table entirely for that kind; leaving
/// it `None` preserves the original table verbatim including section-level
/// comments. Wire values match `RulesEntry` from the load side.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EditedRules {
    #[serde(default)]
    pub level_settings: Option<Vec<RulesEntry>>,
    #[serde(default)]
    pub level_chances: Option<Vec<RulesEntry>>,
    #[serde(default)]
    pub monster_chances: Option<Vec<RulesEntry>>,
}

/// Payload for save_vanilla_level. The frontend ships the FULL templates
/// list on every save (name, comment, rooms with grids/settings/comments),
/// so add/remove/rename/comment on templates and rooms all round-trip by
/// simply being present or absent from the list. The templates section is
/// rebuilt from scratch; everything else on disk (level settings, chances,
/// monsters, section comments) round-trips verbatim.
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EditedTemplate {
    pub name: String,
    #[serde(default)]
    pub comment: Option<String>,
    pub rooms: Vec<EditedRoom>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EditedRoom {
    pub foreground: Vec<Vec<String>>,
    pub background: Vec<Vec<String>>,
    /// Lowercase template-setting names (`"flip"`, `"dual"`, ...). Unknown
    /// strings are ignored on save.
    #[serde(default)]
    pub settings: Vec<String>,
    #[serde(default)]
    pub comment: Option<String>,
}

/// Writes a vanilla level back to `<pack>/Data/Levels/<file>`. Reloads the
/// source (pack copy if present, else the vanilla extract), rebuilds the
/// templates section from the full payload the frontend ships, updates
/// TileCodes to the current palette, backs up, writes cp1252. Level
/// settings, chances, monsters, and each section's comment round-trip
/// verbatim from the on-disk source.
#[tauri::command]
pub async fn save_vanilla_level(
    pack: String,
    file_name: String,
    edited_templates: Vec<EditedTemplate>,
    palette: Vec<SavePaletteEntry>,
    edited_rules: Option<EditedRules>,
    // Desired end-state of the per-file theme override. `theme = None` means
    // "no override" (reset to filename-derived); the marker is stripped if
    // one exists. The comment is only rewritten when this differs from what's
    // already on disk, so ordinary saves never reflow an author's banner.
    theme: Option<i32>,
    subtheme: Option<i32>,
) -> Result<(), String> {
    let sanitized = validate_pack_name(&pack)?;
    if file_name.contains("..") || file_name.starts_with('/') || file_name.starts_with('\\') {
        return Err(format!("invalid level file: {file_name:?}"));
    }
    let (source_path, _) = resolve_vanilla_level_path(&pack, &file_name)?;
    let install_dir = crate::config::load()
        .install_dir
        .ok_or_else(|| "install directory not configured".to_string())?;
    let target_path = install_dir
        .join("Mods")
        .join("Packs")
        .join(&sanitized)
        .join("Data")
        .join("Levels")
        .join(&file_name);
    let backup_dir = install_dir.join("Mods").join("Backups").join(&sanitized);

    tauri::async_runtime::spawn_blocking(move || {
        save_vanilla_level_sync(
            source_path,
            target_path,
            backup_dir,
            edited_templates,
            palette,
            edited_rules,
            theme,
            subtheme,
        )
    })
    .await
    .map_err(|e| format!("save task panicked: {e}"))?
}

#[allow(clippy::too_many_arguments)]
fn save_vanilla_level_sync(
    source_path: PathBuf,
    target_path: PathBuf,
    backup_dir: PathBuf,
    edited_templates: Vec<EditedTemplate>,
    palette: Vec<SavePaletteEntry>,
    edited_rules: Option<EditedRules>,
    theme: Option<i32>,
    subtheme: Option<i32>,
) -> Result<(), String> {
    let mut level = LevelFile::from_path(&source_path).map_err(|e| e.to_string())?;

    // Sync the theme marker only when it changed, so an ordinary save never
    // reflows an author's existing top-of-file banner.
    if parse_theme_marker(level.comment.as_deref()) != (theme, subtheme) {
        level.comment = upsert_theme_marker(level.comment.as_deref(), theme, subtheme);
    }

    // Rebuild TileCodes to match the new palette. Preserves the section
    // comment so cosmetic file structure survives.
    let mut new_tile_codes = TileCodes::new();
    new_tile_codes.comment = level.tile_codes.comment.clone();
    for p in &palette {
        new_tile_codes.set(TileCode {
            name: p.name.clone(),
            value: p.code.clone(),
            comment: p.comment.clone(),
        });
    }
    level.tile_codes = new_tile_codes;

    // Build name -> code lookup.
    let mut name_to_code: std::collections::HashMap<String, char> =
        std::collections::HashMap::new();
    for p in &palette {
        if let Some(ch) = p.code.chars().next() {
            name_to_code.insert(p.name.clone(), ch);
        }
    }
    let empty_code = name_to_code.get("empty").copied().unwrap_or('0');

    // Rebuild the templates section wholesale from the payload. Any
    // template on disk that isn't in `edited_templates` is dropped; any
    // template in `edited_templates` that wasn't on disk is added. Order
    // in the payload dictates on-disk order.
    let mut new_templates = LevelTemplates::new();
    new_templates.comment = level.level_templates.comment.clone();
    for tpl in edited_templates {
        let rooms: Vec<Room> = tpl
            .rooms
            .into_iter()
            .map(|r| Room {
                comment: r.comment,
                settings: r
                    .settings
                    .iter()
                    .filter_map(|n| parse_template_setting(n))
                    .collect(),
                foreground: names_grid_to_chars(&r.foreground, &name_to_code, empty_code),
                background: names_grid_to_chars(&r.background, &name_to_code, empty_code),
            })
            .collect();
        new_templates.set(LevelTemplate {
            name: tpl.name,
            comment: tpl.comment,
            rooms,
        });
    }
    level.level_templates = new_templates;

    // Apply rules overrides last so they see the same section comments the
    // original file carried on those tables.
    if let Some(rules) = edited_rules {
        if let Some(entries) = rules.level_settings {
            let section_comment = level.level_settings.comment.clone();
            let mut next = LevelSettings::new();
            next.comment = section_comment;
            for entry in entries {
                match LevelSetting::parse(&format!("\\-{} {}", entry.name, entry.value.trim())) {
                    Ok(mut parsed) => {
                        parsed.comment = entry.comment;
                        next.set(parsed);
                    }
                    Err(e) => {
                        tracing::warn!(
                            target: "level_editor",
                            "dropping invalid level setting {}={}: {}",
                            entry.name, entry.value, e
                        );
                    }
                }
            }
            level.level_settings = next;
        }
        if let Some(entries) = rules.level_chances {
            let section_comment = level.level_chances.comment.clone();
            let mut next = LevelChances::new();
            next.comment = section_comment;
            for entry in entries {
                match LevelChance::parse(&format!("\\%{} {}", entry.name, entry.value.trim())) {
                    Ok(mut parsed) => {
                        parsed.comment = entry.comment;
                        next.set(parsed);
                    }
                    Err(e) => {
                        tracing::warn!(
                            target: "level_editor",
                            "dropping invalid level chance {}={}: {}",
                            entry.name, entry.value, e
                        );
                    }
                }
            }
            level.level_chances = next;
        }
        if let Some(entries) = rules.monster_chances {
            let section_comment = level.monster_chances.comment.clone();
            let mut next = MonsterChances::new();
            next.comment = section_comment;
            for entry in entries {
                match MonsterChance::parse(&format!("\\+{} {}", entry.name, entry.value.trim())) {
                    Ok(mut parsed) => {
                        parsed.comment = entry.comment;
                        next.set(parsed);
                    }
                    Err(e) => {
                        tracing::warn!(
                            target: "level_editor",
                            "dropping invalid monster chance {}={}: {}",
                            entry.name, entry.value, e
                        );
                    }
                }
            }
            level.monster_chances = next;
        }
    }

    if let Some(parent) = target_path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| format!("mkdir {}: {e}", parent.display()))?;
    }
    if let Err(e) = make_backup(&target_path, &backup_dir) {
        tracing::warn!(target: "level_editor", "backup failed for {}: {}", target_path.display(), e);
    }
    level.write_path(&target_path).map_err(|e| e.to_string())?;
    Ok(())
}

/// Maps a lowercase setting name back to the ml2_levels enum. Matches
/// `TemplateSetting::as_str` on the encode side.
fn parse_template_setting(name: &str) -> Option<ml2_levels::TemplateSetting> {
    use ml2_levels::TemplateSetting as TS;
    match name {
        "ignore" => Some(TS::Ignore),
        "flip" => Some(TS::Flip),
        "onlyflip" => Some(TS::OnlyFlip),
        "dual" => Some(TS::Dual),
        "rare" => Some(TS::Rare),
        "hard" => Some(TS::Hard),
        "liquid" => Some(TS::Liquid),
        "purge" => Some(TS::Purge),
        _ => None,
    }
}

fn names_grid_to_chars(
    grid: &[Vec<String>],
    name_to_code: &std::collections::HashMap<String, char>,
    empty_code: char,
) -> Vec<Vec<char>> {
    grid.iter()
        .map(|row| {
            row.iter()
                .map(|name| {
                    if name.is_empty() {
                        empty_code
                    } else {
                        name_to_code.get(name).copied().unwrap_or(empty_code)
                    }
                })
                .collect()
        })
        .collect()
}

#[cfg(test)]
mod theme_marker_tests {
    use super::*;

    /// Reading back the theme a marker encodes.
    #[test]
    fn parses_theme_and_subtheme() {
        let comment = "// ------------------------------\n// modlunky2: theme=jungle\n";
        assert_eq!(parse_theme_marker(Some(comment)), (Some(2), None));

        let co = "// modlunky2: theme=cosmicocean subtheme=abzu\n";
        assert_eq!(parse_theme_marker(Some(co)), (Some(10), Some(13)));

        assert_eq!(parse_theme_marker(None), (None, None));
        assert_eq!(
            parse_theme_marker(Some("// just an author banner\n")),
            (None, None)
        );
    }

    /// The `//!` sigil normalizes to `// ! ...` on write; the token match
    /// must still recognize the line afterward.
    #[test]
    fn matches_marker_after_prefix_normalization() {
        assert!(is_theme_marker_line("//! modlunky2: theme=jungle"));
        assert!(is_theme_marker_line("// ! modlunky2: theme=jungle"));
        assert!(is_theme_marker_line("// modlunky2: theme=jungle"));
        assert!(!is_theme_marker_line("// modlunky is cool"));
    }

    /// Setting a theme on a file with no prior banner produces a dash-fenced
    /// block that the parser re-captures -- i.e. it round-trips.
    #[test]
    fn insert_then_reparse_round_trips() {
        let built = upsert_theme_marker(None, Some(2), None).unwrap();
        assert!(built.starts_with(SECTION_COMMENT));
        // Round-trip through the actual writer + parser.
        let file = LevelFile {
            comment: Some(built),
            ..Default::default()
        };
        let serialized = file.to_string().unwrap();
        let reparsed = LevelFile::from_str(&serialized).unwrap();
        assert_eq!(
            parse_theme_marker(reparsed.comment.as_deref()),
            (Some(2), None)
        );
    }

    /// Reset (theme = None) on a marker-only banner leaves nothing behind.
    #[test]
    fn reset_drops_marker_only_banner() {
        let marker_only = "// ------------------------------\n// modlunky2: theme=jungle\n";
        assert_eq!(upsert_theme_marker(Some(marker_only), None, None), None);
    }

    /// Reset preserves an author's banner text, dropping only our line.
    #[test]
    fn reset_preserves_author_banner() {
        let with_author =
            "// ------------------------------\n// My cool pack\n// modlunky2: theme=jungle\n";
        let after = upsert_theme_marker(Some(with_author), None, None).unwrap();
        assert!(after.contains("My cool pack"));
        assert!(!after.to_ascii_lowercase().contains("modlunky2:"));
        // Still a valid, re-capturable block.
        assert!(after.starts_with(SECTION_COMMENT));
    }

    /// Updating an existing marker keeps the author banner and swaps the theme.
    #[test]
    fn update_swaps_theme_keeps_author_text() {
        let before =
            "// ------------------------------\n// My cool pack\n// modlunky2: theme=jungle\n";
        let after = upsert_theme_marker(Some(before), Some(6), None).unwrap();
        assert!(after.contains("My cool pack"));
        assert_eq!(parse_theme_marker(Some(&after)), (Some(6), None));
    }
}
