mod characters;
mod config;
mod extract;
mod fonts;
mod fyi_ws;
mod level_editor;
mod log_buffer;
mod mods;
mod overlunky;
mod paths;
mod playlunky;
mod state;
mod toast_buffer;
mod trackers;
mod updater;
mod window_icon;

use std::collections::HashSet;
use std::sync::{Arc, Mutex};

use state::AppState;
use tauri::Manager;

#[tauri::command]
fn app_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

pub fn run() {
    use tracing_subscriber::layer::SubscriberExt;
    use tracing_subscriber::util::SubscriberInitExt;

    // fmt layer writes to stderr (debug console when launched from a
    // terminal, the OS's stderr pipe otherwise); log_buffer captures the
    // same events into the ring buffer the Logs modal reads. Both share
    // one EnvFilter so RUST_LOG applies to both.
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info")),
        )
        .with(tracing_subscriber::fmt::layer())
        .with(log_buffer::LogBufferLayer)
        .init();

    tauri::Builder::default()
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        // Persists each window's size + position and restores on next
        // launch. The plugin clamps the restored geometry to the
        // currently connected monitors so an off-screen state (external
        // display unplugged, etc.) doesn't leave the window inaccessible.
        //
        // VISIBLE is masked off the default flag set: the main window is
        // configured `visible: false` so the frontend can hide the
        // white flash + tab-restore reflow, and the plugin's default
        // behavior of restoring the last-seen visibility would override
        // that on every launch after the first.
        .plugin(
            tauri_plugin_window_state::Builder::default()
                .with_state_flags(
                    tauri_plugin_window_state::StateFlags::all()
                        & !tauri_plugin_window_state::StateFlags::VISIBLE,
                )
                .build(),
        )
        .setup(|app| {
            let updates_available = Arc::new(Mutex::new(HashSet::new()));
            let slot = mods::initial_setup(updates_available.clone(), app.handle().clone());
            let fyi_ws_slot = fyi_ws::new_slot();
            app.manage(AppState::new(slot, updates_available, fyi_ws_slot));

            // Kick off the spelunky.fyi push-install listener if the
            // user has a token configured. Fire-and-forget: failure
            // just means the site's "Install" button won't route here
            // until the user fixes their token.
            fyi_ws::start_if_configured(app.handle());

            // Wire the log ring buffer to the app handle so new entries
            // emit `log-line` events for the Logs modal's live tail.
            // Events fired before this point sit in the buffer and get
            // picked up by the modal's initial snapshot fetch.
            log_buffer::install_emitter(app.handle().clone());

            // Auto-start the tracker server if the user had it running
            // last time. Silent on failure (bad port, port already
            // taken) so the app still boots, the user can start
            // manually from the Trackers page.
            let cfg = config::load();
            if cfg.tracker_server_auto_start {
                let handle = app.handle().clone();
                let port = cfg.tracker_server_port;
                tauri::async_runtime::spawn(async move {
                    let state = handle.state::<AppState>();
                    if let Err(e) = trackers::start_tracker_server(Some(port), state).await {
                        tracing::warn!("tracker server auto-start failed: {e}");
                    }
                });
            }

            // Keep the Playlunky release cache fresh on long sessions so
            // the version modal doesn't serve month-old data if the user
            // never closes the app.
            tauri::async_runtime::spawn(playlunky::background_release_refresh_loop());

            // Replace the default (blurry, single-size) window icon on
            // the main window with hand-picked 16x16 + 32x32 frames
            // from icon.ico. See window_icon.rs for the why.
            if let Some(main) = app.get_webview_window("main")
                && let Err(e) = window_icon::apply_window_icon(&main)
            {
                tracing::warn!("failed to set crisp window icon on main: {e}");
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            app_version,
            updater::get_modlunky_version,
            updater::install_update,
            config::get_config,
            config::set_config,
            fyi_ws::get_fyi_ws_status,
            fyi_ws::refresh_fyi_ws,
            log_buffer::get_recent_logs,
            log_buffer::clear_logs,
            log_buffer::open_logs_window,
            toast_buffer::record_toast,
            toast_buffer::get_recent_toasts,
            toast_buffer::clear_toasts,
            mods::list_mods,
            mods::refresh_mods,
            mods::get_load_order,
            mods::set_load_order,
            mods::get_mod_logo,
            mods::remove_mod,
            mods::open_mod_folder,
            mods::update_mod,
            mods::install_from_fyi,
            mods::install_from_local,
            mods::list_pack_ids,
            mods::rebuild_mods,
            mods::check_fyi_updates,
            mods::clear_playlunky_cache,
            paths::guess_install_dir,
            paths::open_directory,
            playlunky::list_installed_playlunky,
            playlunky::list_playlunky_releases,
            playlunky::download_playlunky_version,
            playlunky::remove_playlunky_version,
            playlunky::launch_playlunky,
            playlunky::get_playlunky_options,
            playlunky::set_playlunky_options,
            playlunky::sync_desktop_shortcut,
            extract::list_extractable_exes,
            extract::extract_assets,
            extract::get_extract_status,
            extract::extracted_assets_available,
            level_editor::build_editor_atlas,
            level_editor::list_level_packs,
            level_editor::create_level_pack,
            level_editor::open_level_editor_window,
            level_editor::list_recent_packs,
            level_editor::push_recent_pack,
            level_editor::remove_recent_pack,
            level_editor::get_level_sequence_status,
            level_editor::check_latest_level_sequence,
            level_editor::install_level_sequence,
            level_editor::list_custom_levels,
            level_editor::open_room_preview_window,
            level_editor::open_level_file,
            level_editor::open_level_file_with,
            level_editor::load_custom_level,
            level_editor::build_tile_name_atlas,
            level_editor::get_tile_sprite,
            level_editor::get_tile_sprite_natural,
            level_editor::render_tile_sprites,
            level_editor::list_short_codes,
            level_editor::list_valid_tile_codes,
            level_editor::list_valid_level_settings,
            level_editor::list_valid_level_chances,
            level_editor::list_valid_monster_chances,
            level_editor::get_biome_background,
            level_editor::get_cosmic_backdrop,
            level_editor::get_cosmic_subtheme_decoration,
            level_editor::save_custom_level,
            level_editor::load_custom_config,
            level_editor::save_custom_config,
            level_editor::create_custom_level,
            level_editor::rename_custom_level,
            level_editor::delete_custom_level,
            level_editor::list_custom_save_formats,
            level_editor::add_custom_save_format,
            level_editor::remove_custom_save_format,
            level_editor::get_default_save_format,
            level_editor::set_default_save_format,
            characters::get_characters,
            characters::get_character_preview,
            characters::get_vanilla_character_preview,
            characters::set_character_ignored,
            characters::set_character_confirmed,
            characters::assign_character,
            characters::disable_character,
            characters::unassign_character,
            characters::restore_character,
            characters::open_character_chooser_window,
            level_editor::get_editor_prefs,
            level_editor::set_editor_prefs,
            level_editor::list_vanilla_levels,
            level_editor::load_vanilla_level,
            level_editor::save_vanilla_level,
            overlunky::is_overlunky_installed,
            overlunky::download_overlunky,
            overlunky::launch_overlunky,
            trackers::start_tracker_server,
            trackers::stop_tracker_server,
            trackers::get_tracker_server_status,
            trackers::get_tracker_payload,
            trackers::get_tracker_config,
            trackers::set_tracker_config,
            trackers::open_tracker_window,
            trackers::get_window_config,
            trackers::set_window_config,
            fonts::list_system_fonts,
            trackers::get_tracker_always_on_top,
            trackers::set_tracker_always_on_top,
            trackers::get_file_settings,
            trackers::set_file_settings,
            trackers::get_tracker_file_path,
            trackers::open_tracker_file_dir,
            trackers::get_tracker_diagnostics,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
