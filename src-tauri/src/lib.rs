//! Library crate for the Tauri app. `main.rs` calls [`run`] from here.

pub mod capture;
pub mod coach;
pub mod commands;
pub mod config;
pub mod game_state;
pub mod gemini;
pub mod hotkeys;
pub mod ocr;
pub mod overlay;
pub mod secrets;
pub mod tracker;

use std::sync::Arc;
use tracing_subscriber::EnvFilter;

use crate::coach::CoachState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .try_init();

    let state = Arc::new(CoachState::default());

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(state)
        .setup(|app| {
            if let Err(e) = hotkeys::register(app.handle()) {
                tracing::warn!(?e, "failed to register global hotkeys");
            }
            // Ensure the overlay starts hidden and click-through.
            let handle = app.handle().clone();
            let _ = overlay::set_click_through(&handle, true);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::save_secret,
            commands::has_secret,
            commands::delete_secret,
            commands::load_config,
            commands::save_config,
            commands::fetch_profile,
            commands::fetch_match_history,
            commands::test_gemini,
            commands::preview_coach,
            commands::start_coach,
            commands::stop_coach,
            commands::open_overlay,
            commands::close_overlay,
            commands::set_overlay_click_through,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
