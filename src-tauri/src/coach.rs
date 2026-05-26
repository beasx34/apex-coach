//! Real-time coaching loop. Runs as a Tokio task:
//!
//! 1. Sleep `interval_ms`.
//! 2. Capture primary monitor → crop HUD ROIs → OCR each one.
//! 3. Build `GameContext`. Skip Gemini if context didn't meaningfully change.
//! 4. POST to Gemini; emit `coach://advice` to the overlay window.

use std::sync::Arc;
use std::time::{Duration, Instant};

use anyhow::{anyhow, Result};
use serde::Serialize;
use tauri::{AppHandle, Emitter};
use tokio::sync::{oneshot, Mutex};

use crate::capture::capture_primary;
use crate::config::UserConfig;
use crate::game_state::{parse_from_frame, GameContext};
use crate::gemini::GeminiClient;
use crate::ocr::make_backend;
use crate::secrets;
use crate::tracker::{Profile, TrackerClient};

#[derive(Debug, Default, Serialize, Clone, Copy)]
pub struct CoachStatus {
    pub running: bool,
}

#[derive(Default)]
pub struct CoachState {
    pub handle: Mutex<Option<oneshot::Sender<()>>>,
    pub last_emit: Mutex<Option<Instant>>,
}

/// Spawn the coach loop. Returns immediately; cancel via `stop`.
pub async fn start(app: AppHandle, state: Arc<CoachState>, cfg: UserConfig) -> Result<()> {
    let mut guard = state.handle.lock().await;
    if guard.is_some() {
        return Ok(());
    }
    let (tx, rx) = oneshot::channel::<()>();
    *guard = Some(tx);
    drop(guard);

    let app_for_emit = app.clone();
    app_for_emit
        .emit("coach://status", CoachStatus { running: true })
        .ok();

    let gemini_key = secrets::get(secrets::GEMINI_KEY)
        .map_err(|_| anyhow!("Gemini API key is not set. Add it in Settings."))?;
    let tracker_key = secrets::get(secrets::TRACKER_KEY).ok();

    let gemini = Arc::new(GeminiClient::new(
        gemini_key,
        cfg.gemini_model.clone(),
        cfg.language.clone(),
    ));
    let tracker = tracker_key.map(|k| Arc::new(TrackerClient::new(k, cfg.tracker_provider)));
    let ocr = make_backend()?;
    let cfg_arc = Arc::new(cfg);
    let app_loop = app.clone();
    let state_loop = state.clone();

    tokio::spawn(async move {
        let mut rx = rx;
        let mut last_ctx: GameContext = GameContext::default();
        let mut cached_profile: Option<Profile> = None;
        let interval = Duration::from_millis(cfg_arc.coach_interval_ms.max(500));
        let min_gemini_interval = Duration::from_millis(4000);

        if let Some(t) = &tracker {
            if !cfg_arc.player_name.is_empty() {
                match t
                    .fetch_profile(cfg_arc.platform, &cfg_arc.player_name)
                    .await
                {
                    Ok(p) => cached_profile = Some(p),
                    Err(e) => tracing::warn!(?e, "tracker profile fetch failed"),
                }
            }
        }

        loop {
            tokio::select! {
                _ = &mut rx => {
                    tracing::info!("coach loop stop requested");
                    break;
                }
                _ = tokio::time::sleep(interval) => {}
            }

            let frame = match tokio::task::spawn_blocking(capture_primary).await {
                Ok(Ok(f)) => f,
                Ok(Err(e)) => {
                    tracing::warn!(?e, "capture failed");
                    continue;
                }
                Err(e) => {
                    tracing::warn!(?e, "capture task panicked");
                    continue;
                }
            };

            let ctx = match parse_from_frame(&frame, &cfg_arc.rois, ocr.as_ref(), &cfg_arc).await {
                Ok(c) => c,
                Err(e) => {
                    tracing::warn!(?e, "OCR/parse failed");
                    continue;
                }
            };

            if !ctx.has_signal() {
                continue;
            }
            if !meaningful_change(&last_ctx, &ctx) {
                continue;
            }

            {
                let mut last_emit = state_loop.last_emit.lock().await;
                if let Some(prev) = *last_emit {
                    if prev.elapsed() < min_gemini_interval {
                        continue;
                    }
                }
                *last_emit = Some(Instant::now());
            }

            match gemini.coach(&ctx, cached_profile.as_ref()).await {
                Ok(advice) => {
                    if let Err(e) = app_loop.emit("coach://advice", &advice) {
                        tracing::warn!(?e, "emit advice failed");
                    }
                    last_ctx = ctx;
                }
                Err(e) => tracing::warn!(?e, "gemini call failed"),
            }
        }

        app_loop
            .emit("coach://status", CoachStatus { running: false })
            .ok();
        let mut guard = state_loop.handle.lock().await;
        *guard = None;
    });

    Ok(())
}

pub async fn stop(state: Arc<CoachState>) -> Result<()> {
    let mut guard = state.handle.lock().await;
    if let Some(tx) = guard.take() {
        let _ = tx.send(());
    }
    Ok(())
}

/// Decide whether the new context is interesting enough to spend a Gemini call.
pub fn meaningful_change(prev: &GameContext, cur: &GameContext) -> bool {
    if prev.kills != cur.kills && cur.kills.is_some() {
        return true;
    }
    if prev.squads_left != cur.squads_left && cur.squads_left.is_some() {
        return true;
    }
    if let (Some(pm), Some(cm)) = (prev.ammo_in_mag, cur.ammo_in_mag) {
        if cm + 5 <= pm || cm <= 5 && pm > cm {
            return true;
        }
    }
    if prev.ring_phase != cur.ring_phase {
        return true;
    }
    if let (Some(pd), Some(cd)) = (prev.damage, cur.damage) {
        if cd >= pd + 200 {
            return true;
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn change_on_new_kill() {
        let mut a = GameContext::default();
        let mut b = GameContext::default();
        a.kills = Some(2);
        b.kills = Some(3);
        assert!(meaningful_change(&a, &b));
    }

    #[test]
    fn no_change_when_identical() {
        let ctx = GameContext::default();
        assert!(!meaningful_change(&ctx, &ctx));
    }
}
