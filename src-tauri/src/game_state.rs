//! Parses OCR strings from HUD ROIs into a structured `GameContext` that we
//! feed to Gemini. Defensive: anything we can't parse stays `None` so the
//! coach prompt simply doesn't mention it.

use anyhow::Result;
use serde::{Deserialize, Serialize};

use crate::capture::{crop, Frame};
use crate::config::{GameMode, HudRois, UserConfig};
use crate::ocr::OcrBackend;

#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct GameContext {
    pub legend: Option<String>,
    pub mode: GameMode,
    pub ammo_in_mag: Option<u32>,
    pub ammo_reserve: Option<u32>,
    pub squads_left: Option<u32>,
    pub players_left: Option<u32>,
    pub kills: Option<u32>,
    pub damage: Option<u32>,
    pub ring_phase: Option<u32>,
    pub time_to_close_secs: Option<u32>,
    pub timestamp_ms: u64,
}

impl GameContext {
    /// Returns true if at least one HUD field was successfully parsed.
    pub fn has_signal(&self) -> bool {
        self.ammo_in_mag.is_some()
            || self.squads_left.is_some()
            || self.kills.is_some()
            || self.damage.is_some()
            || self.time_to_close_secs.is_some()
    }
}

/// Runs OCR over each ROI and assembles a `GameContext`.
pub async fn parse_from_frame(
    frame: &Frame,
    rois: &HudRois,
    ocr: &dyn OcrBackend,
    cfg: &UserConfig,
) -> Result<GameContext> {
    let ammo_text = ocr.recognize(&crop(frame, rois.ammo)).await?;
    let squads_text = ocr.recognize(&crop(frame, rois.squads_left)).await?;
    let kills_text = ocr.recognize(&crop(frame, rois.kills)).await?;
    let damage_text = ocr.recognize(&crop(frame, rois.damage)).await?;
    let ring_text = ocr.recognize(&crop(frame, rois.ring_timer)).await?;

    let (ammo_in_mag, ammo_reserve) = extract_ammo_pair(&ammo_text);
    let squads_left = extract_digits(&squads_text);
    let kills = extract_digits(&kills_text);
    let damage = extract_digits(&damage_text);
    let time_to_close_secs = extract_timer(&ring_text);

    Ok(GameContext {
        legend: None,
        mode: cfg.mode,
        ammo_in_mag,
        ammo_reserve,
        squads_left,
        players_left: None,
        kills,
        damage,
        ring_phase: None,
        time_to_close_secs,
        timestamp_ms: now_ms(),
    })
}

/// Extracts the first run of digits from an arbitrary OCR string.
pub fn extract_digits(s: &str) -> Option<u32> {
    let mut buf = String::new();
    for c in s.chars() {
        if c.is_ascii_digit() {
            buf.push(c);
        } else if !buf.is_empty() {
            break;
        }
    }
    buf.parse::<u32>().ok()
}

/// Parses Apex ammo HUD: "30 / 90" -> (Some(30), Some(90)). The slash sometimes
/// OCRs as `1`, `7`, `/`, `\` — we accept any non-digit as separator.
pub fn extract_ammo_pair(s: &str) -> (Option<u32>, Option<u32>) {
    let mut groups: Vec<u32> = Vec::new();
    let mut cur = String::new();
    for c in s.chars() {
        if c.is_ascii_digit() {
            cur.push(c);
        } else if !cur.is_empty() {
            if let Ok(n) = cur.parse() {
                groups.push(n);
            }
            cur.clear();
        }
    }
    if !cur.is_empty() {
        if let Ok(n) = cur.parse() {
            groups.push(n);
        }
    }
    match groups.len() {
        0 => (None, None),
        1 => (Some(groups[0]), None),
        _ => (Some(groups[0]), Some(groups[1])),
    }
}

/// Parses a `m:ss` or `mm:ss` ring timer into total seconds.
pub fn extract_timer(s: &str) -> Option<u32> {
    let mut parts: Vec<u32> = Vec::new();
    let mut cur = String::new();
    for c in s.chars() {
        if c.is_ascii_digit() {
            cur.push(c);
        } else if !cur.is_empty() {
            if let Ok(n) = cur.parse() {
                parts.push(n);
            }
            cur.clear();
        }
    }
    if !cur.is_empty() {
        if let Ok(n) = cur.parse() {
            parts.push(n);
        }
    }
    match parts.as_slice() {
        [m, sec] => Some(m * 60 + sec.min(&59)),
        [sec] => Some(*sec),
        _ => None,
    }
}

fn now_ms() -> u64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ammo_pair_parses() {
        assert_eq!(extract_ammo_pair("30 / 90"), (Some(30), Some(90)));
        assert_eq!(extract_ammo_pair("7\\210"), (Some(7), Some(210)));
        assert_eq!(extract_ammo_pair("∞"), (None, None));
        assert_eq!(extract_ammo_pair("42"), (Some(42), None));
    }

    #[test]
    fn timer_parses() {
        assert_eq!(extract_timer("1:24"), Some(84));
        assert_eq!(extract_timer("0:09"), Some(9));
        assert_eq!(extract_timer("15"), Some(15));
        assert_eq!(extract_timer(""), None);
    }

    #[test]
    fn digits_handle_garbage() {
        assert_eq!(extract_digits("Kills 4"), Some(4));
        assert_eq!(extract_digits("none"), None);
        assert_eq!(extract_digits("12abc34"), Some(12));
    }
}
