//! Tauri invoke handlers — every `#[tauri::command]` here is callable from the
//! frontend via `invoke("name", args)`. Errors are stringified because the
//! frontend never needs the Rust error type.

use std::sync::Arc;

use tauri::{AppHandle, Manager};

use crate::coach::{self, CoachState};
use crate::config::{self, Platform, UserConfig, UserConfigDto};
use crate::game_state::GameContext;
use crate::gemini::{Category, CoachAdvice, GeminiClient, Priority};
use crate::overlay;
use crate::secrets;
use crate::tracker::{MatchRow, Profile, TrackerClient};

fn to_str_err<E: std::fmt::Display>(e: E) -> String {
    format!("{e}")
}

#[tauri::command]
pub fn save_secret(name: String, value: String) -> Result<(), String> {
    if !secrets::is_known(&name) {
        return Err(format!("unknown secret name: {name}"));
    }
    secrets::put(&name, &value).map_err(to_str_err)
}

#[tauri::command]
pub fn has_secret(name: String) -> Result<bool, String> {
    if !secrets::is_known(&name) {
        return Err(format!("unknown secret name: {name}"));
    }
    Ok(secrets::has(&name))
}

#[tauri::command]
pub fn delete_secret(name: String) -> Result<(), String> {
    if !secrets::is_known(&name) {
        return Err(format!("unknown secret name: {name}"));
    }
    secrets::delete(&name).map_err(to_str_err)
}

#[tauri::command]
pub fn load_config(app: AppHandle) -> Result<UserConfigDto, String> {
    let cfg = config::load(&app).map_err(to_str_err)?;
    Ok(UserConfigDto::from(&cfg))
}

#[tauri::command]
pub fn save_config(app: AppHandle, cfg: UserConfigDto) -> Result<(), String> {
    let cfg: UserConfig = cfg.into();
    config::save(&app, &cfg).map_err(to_str_err)
}

#[tauri::command]
pub async fn fetch_profile(
    app: AppHandle,
    platform: Platform,
    name: String,
) -> Result<Profile, String> {
    let cfg = config::load(&app).map_err(to_str_err)?;
    let key = secrets::get(secrets::TRACKER_KEY)
        .map_err(|_| "Apex tracker API key is not set. Add it in Settings.".to_string())?;
    let client = TrackerClient::new(key, cfg.tracker_provider);
    client
        .fetch_profile(platform, &name)
        .await
        .map_err(to_str_err)
}

#[tauri::command]
pub async fn fetch_match_history(
    app: AppHandle,
    platform: Platform,
    name: String,
) -> Result<Vec<MatchRow>, String> {
    let cfg = config::load(&app).map_err(to_str_err)?;
    let key = secrets::get(secrets::TRACKER_KEY)
        .map_err(|_| "Apex tracker API key is not set. Add it in Settings.".to_string())?;
    let client = TrackerClient::new(key, cfg.tracker_provider);
    client
        .fetch_match_history(platform, &name)
        .await
        .map_err(to_str_err)
}

#[tauri::command]
pub async fn test_gemini(app: AppHandle) -> Result<String, String> {
    let cfg = config::load(&app).map_err(to_str_err)?;
    let key = secrets::get(secrets::GEMINI_KEY)
        .map_err(|_| "Gemini API key is not set. Add it in Settings.".to_string())?;
    let client = GeminiClient::new(key, cfg.gemini_model, cfg.language);
    client.ping().await.map_err(to_str_err)
}

#[tauri::command]
pub async fn preview_coach(app: AppHandle) -> Result<CoachAdvice, String> {
    let cfg = config::load(&app).map_err(to_str_err)?;
    let key = secrets::get(secrets::GEMINI_KEY)
        .map_err(|_| "Gemini API key is not set. Add it in Settings.".to_string())?;
    let client = GeminiClient::new(key, cfg.gemini_model.clone(), cfg.language.clone());
    let ctx = GameContext {
        mode: cfg.mode,
        ammo_in_mag: Some(7),
        ammo_reserve: Some(40),
        squads_left: Some(8),
        kills: Some(1),
        damage: Some(420),
        time_to_close_secs: Some(45),
        ..Default::default()
    };
    match client.coach(&ctx, None).await {
        Ok(a) => Ok(a),
        Err(e) => {
            // Even if Gemini failed, return a placeholder so the UI doesn't break
            // — but propagate the error message.
            tracing::warn!(?e, "preview coach failed");
            Err(to_str_err(e))
        }
    }
}

#[tauri::command]
pub async fn start_coach(app: AppHandle) -> Result<(), String> {
    let cfg = config::load(&app).map_err(to_str_err)?;
    let state: Arc<CoachState> = app
        .try_state::<Arc<CoachState>>()
        .map(|s| s.inner().clone())
        .unwrap_or_else(|| Arc::new(CoachState::default()));
    coach::start(app, state, cfg).await.map_err(to_str_err)
}

#[tauri::command]
pub async fn stop_coach(app: AppHandle) -> Result<(), String> {
    let state: Arc<CoachState> = app
        .try_state::<Arc<CoachState>>()
        .map(|s| s.inner().clone())
        .unwrap_or_else(|| Arc::new(CoachState::default()));
    coach::stop(state).await.map_err(to_str_err)
}

#[tauri::command]
pub fn open_overlay(app: AppHandle) -> Result<(), String> {
    overlay::show(&app).map_err(to_str_err)
}

#[tauri::command]
pub fn close_overlay(app: AppHandle) -> Result<(), String> {
    overlay::hide(&app).map_err(to_str_err)
}

#[tauri::command]
pub fn set_overlay_click_through(app: AppHandle, on: bool) -> Result<(), String> {
    overlay::set_click_through(&app, on).map_err(to_str_err)
}

// Re-export Category and Priority so frontend bindings could be generated if
// desired; the variants serialize as strings matching the React types.
#[allow(dead_code)]
fn _type_assertion(_: Priority, _: Category) {}
