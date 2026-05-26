//! Overlay window helpers. The overlay window is declared in `tauri.conf.json`
//! and starts hidden; we just toggle visibility / click-through here.

use anyhow::{anyhow, Result};
use tauri::{AppHandle, Manager, WebviewWindow};

const OVERLAY_LABEL: &str = "overlay";

fn overlay_window(app: &AppHandle) -> Result<WebviewWindow> {
    app.get_webview_window(OVERLAY_LABEL)
        .ok_or_else(|| anyhow!("overlay window not found"))
}

pub fn show(app: &AppHandle) -> Result<()> {
    let win = overlay_window(app)?;
    win.show().map_err(anyhow::Error::from)?;
    win.set_always_on_top(true).ok();
    win.set_focus().ok();
    Ok(())
}

pub fn hide(app: &AppHandle) -> Result<()> {
    let win = overlay_window(app)?;
    win.hide().map_err(anyhow::Error::from)?;
    Ok(())
}

pub fn set_click_through(app: &AppHandle, on: bool) -> Result<()> {
    let win = overlay_window(app)?;
    win.set_ignore_cursor_events(on)
        .map_err(anyhow::Error::from)
}
