use std::fs;
use std::path::PathBuf;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum Platform {
    #[default]
    Origin,
    Xbl,
    Psn,
    Switch,
}

impl Platform {
    /// Identifier expected by Mozambiquehe.re / Tracker.gg.
    pub fn as_provider_str(&self) -> &'static str {
        match self {
            Platform::Origin => "PC",
            Platform::Xbl => "X1",
            Platform::Psn => "PS4",
            Platform::Switch => "SWITCH",
        }
    }
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum GameMode {
    #[default]
    BrPubs,
    BrRanked,
    Mixtape,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum OcrEngineChoice {
    #[default]
    WindowsOcr,
    None,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum TrackerProvider {
    #[default]
    Mozambique,
    TrackerGg,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub enum OverlayCorner {
    TopLeft,
    TopRight,
    #[default]
    BottomRight,
    BottomLeft,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct Rect {
    pub x: u32,
    pub y: u32,
    pub w: u32,
    pub h: u32,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct HudRois {
    pub ammo: Rect,
    pub squads_left: Rect,
    pub kills: Rect,
    pub damage: Rect,
    pub ring_timer: Rect,
}

impl HudRois {
    /// Reasonable defaults at 1920x1080. The UI lets users override.
    pub fn defaults_1080p() -> Self {
        Self {
            ammo: Rect {
                x: 1613,
                y: 929,
                w: 250,
                h: 76,
            },
            squads_left: Rect {
                x: 1650,
                y: 43,
                w: 230,
                h: 43,
            },
            kills: Rect {
                x: 768,
                y: 22,
                w: 154,
                h: 43,
            },
            damage: Rect {
                x: 922,
                y: 22,
                w: 154,
                h: 43,
            },
            ring_timer: Rect {
                x: 883,
                y: 54,
                w: 154,
                h: 43,
            },
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct HotkeyConfig {
    pub toggle_coach: String,
    pub toggle_overlay: String,
    pub pause_emit: String,
}

impl Default for HotkeyConfig {
    fn default() -> Self {
        Self {
            toggle_coach: "Ctrl+Shift+C".into(),
            toggle_overlay: "Ctrl+Shift+O".into(),
            pause_emit: "Ctrl+Shift+P".into(),
        }
    }
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct OverlayPos {
    pub corner: OverlayCorner,
    pub offset_x: i32,
    pub offset_y: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct UserConfig {
    pub player_name: String,
    pub platform: Platform,
    pub mode: GameMode,
    pub coach_interval_ms: u64,
    /// 0..1; serialized as f32 string via TOML — store as basis points (0..1000) for Eq.
    pub overlay_opacity_bp: u32,
    pub overlay_position: OverlayPos,
    pub hotkeys: HotkeyConfig,
    pub ocr_engine: OcrEngineChoice,
    pub rois: HudRois,
    pub language: String,
    pub gemini_model: String,
    pub tracker_provider: TrackerProvider,
}

impl Default for UserConfig {
    fn default() -> Self {
        Self {
            player_name: String::new(),
            platform: Platform::default(),
            mode: GameMode::default(),
            coach_interval_ms: 1500,
            overlay_opacity_bp: 850,
            overlay_position: OverlayPos::default(),
            hotkeys: HotkeyConfig::default(),
            ocr_engine: OcrEngineChoice::default(),
            rois: HudRois::defaults_1080p(),
            language: "ru".into(),
            gemini_model: "gemini-2.5-flash".into(),
            tracker_provider: TrackerProvider::default(),
        }
    }
}

/// Serializable view of UserConfig that exposes overlay opacity as a real number (0..1)
/// for the frontend. Internally we still keep an integer-basis-points value so the struct
/// implements Eq for change detection.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserConfigDto {
    pub player_name: String,
    pub platform: Platform,
    pub mode: GameMode,
    pub coach_interval_ms: u64,
    pub overlay_opacity: f32,
    pub overlay_position: OverlayPos,
    pub hotkeys: HotkeyConfig,
    pub ocr_engine: OcrEngineChoice,
    pub rois: HudRois,
    pub language: String,
    pub gemini_model: String,
    pub tracker_provider: TrackerProvider,
}

impl From<&UserConfig> for UserConfigDto {
    fn from(c: &UserConfig) -> Self {
        Self {
            player_name: c.player_name.clone(),
            platform: c.platform,
            mode: c.mode,
            coach_interval_ms: c.coach_interval_ms,
            overlay_opacity: (c.overlay_opacity_bp as f32) / 1000.0,
            overlay_position: c.overlay_position,
            hotkeys: c.hotkeys.clone(),
            ocr_engine: c.ocr_engine,
            rois: c.rois,
            language: c.language.clone(),
            gemini_model: c.gemini_model.clone(),
            tracker_provider: c.tracker_provider,
        }
    }
}

impl From<UserConfigDto> for UserConfig {
    fn from(d: UserConfigDto) -> Self {
        Self {
            player_name: d.player_name,
            platform: d.platform,
            mode: d.mode,
            coach_interval_ms: d.coach_interval_ms,
            overlay_opacity_bp: ((d.overlay_opacity.clamp(0.0, 1.0)) * 1000.0) as u32,
            overlay_position: d.overlay_position,
            hotkeys: d.hotkeys,
            ocr_engine: d.ocr_engine,
            rois: d.rois,
            language: d.language,
            gemini_model: d.gemini_model,
            tracker_provider: d.tracker_provider,
        }
    }
}

fn config_path(app: &AppHandle) -> Result<PathBuf> {
    let dir = app
        .path()
        .app_config_dir()
        .context("could not resolve app_config_dir")?;
    fs::create_dir_all(&dir).context("create app_config_dir")?;
    Ok(dir.join("config.toml"))
}

/// Load `config.toml` from app config dir; return defaults if missing or invalid.
pub fn load(app: &AppHandle) -> Result<UserConfig> {
    let path = config_path(app)?;
    if !path.exists() {
        return Ok(UserConfig::default());
    }
    let raw = fs::read_to_string(&path).with_context(|| format!("reading {}", path.display()))?;
    let cfg: UserConfig = match toml::from_str(&raw) {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!(?e, "failed to parse config.toml; falling back to defaults");
            UserConfig::default()
        }
    };
    Ok(cfg)
}

/// Atomically write the config to disk.
pub fn save(app: &AppHandle, cfg: &UserConfig) -> Result<()> {
    let path = config_path(app)?;
    let tmp = path.with_extension("toml.tmp");
    let serialized = toml::to_string_pretty(cfg).context("serialize config")?;
    fs::write(&tmp, serialized).context("write tmp config")?;
    fs::rename(&tmp, &path).context("rename tmp config")?;
    Ok(())
}
