//! Global hotkeys. Registered through tauri-plugin-global-shortcut. The
//! frontend reads the current bindings out of UserConfig, but the defaults
//! are wired here so the app is usable out of the box.

use std::sync::Arc;

use anyhow::Result;
use tauri::{AppHandle, Manager};
use tauri_plugin_global_shortcut::{
    Code, GlobalShortcutExt, Modifiers, Shortcut, ShortcutEvent, ShortcutState,
};

use crate::coach::CoachState;
use crate::overlay;

pub fn register(app: &AppHandle) -> Result<()> {
    let toggle_coach = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyC);
    let toggle_overlay = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyO);
    let pause_emit = Shortcut::new(Some(Modifiers::CONTROL | Modifiers::SHIFT), Code::KeyP);

    let manager = app.global_shortcut();
    manager.on_shortcut(toggle_coach, on_toggle_coach)?;
    manager.on_shortcut(toggle_overlay, on_toggle_overlay)?;
    manager.on_shortcut(pause_emit, on_pause_emit)?;
    Ok(())
}

fn on_toggle_coach(app: &AppHandle, _shortcut: &Shortcut, event: ShortcutEvent) {
    if !matches!(event.state(), ShortcutState::Pressed) {
        return;
    }
    let app = app.clone();
    let state: Arc<CoachState> = app.state::<Arc<CoachState>>().inner().clone();
    tauri::async_runtime::spawn(async move {
        let running = state.handle.lock().await.is_some();
        if running {
            let _ = crate::coach::stop(state).await;
        } else if let Ok(cfg) = crate::config::load(&app) {
            let _ = overlay::show(&app);
            let _ = crate::coach::start(app, state, cfg).await;
        }
    });
}

fn on_toggle_overlay(app: &AppHandle, _shortcut: &Shortcut, event: ShortcutEvent) {
    if !matches!(event.state(), ShortcutState::Pressed) {
        return;
    }
    if let Some(win) = app.get_webview_window("overlay") {
        let visible = win.is_visible().unwrap_or(false);
        if visible {
            let _ = overlay::hide(app);
        } else {
            let _ = overlay::show(app);
        }
    }
}

fn on_pause_emit(_app: &AppHandle, _shortcut: &Shortcut, event: ShortcutEvent) {
    if !matches!(event.state(), ShortcutState::Pressed) {
        return;
    }
    // Pause is implemented by stopping the loop; users can re-toggle to resume.
    tracing::info!("pause hotkey pressed; stop the coach to pause emissions");
}
