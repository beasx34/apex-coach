//! Cross-platform screen capture (using `xcap`). On Windows we capture the
//! primary monitor; the rest of the pipeline crops the requested HUD ROIs
//! before feeding them into OCR.

use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};

use crate::config::Rect;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Frame {
    pub width: u32,
    pub height: u32,
    /// Raw RGBA8 pixels, top-left origin, row-major (width * 4 bytes per row).
    #[serde(skip)]
    pub rgba: Vec<u8>,
}

impl Frame {
    pub fn new(width: u32, height: u32, rgba: Vec<u8>) -> Self {
        Self {
            width,
            height,
            rgba,
        }
    }
}

/// Capture the primary monitor as RGBA8.
pub fn capture_primary() -> Result<Frame> {
    let monitors = xcap::Monitor::all().context("listing monitors")?;
    let primary = monitors
        .into_iter()
        .find(|m| m.is_primary())
        .or_else(|| xcap::Monitor::all().ok().and_then(|m| m.into_iter().next()))
        .ok_or_else(|| anyhow!("no monitor available"))?;
    let img = primary.capture_image().context("capturing screen")?;
    let (w, h) = (img.width(), img.height());
    let rgba = img.into_raw();
    Ok(Frame::new(w, h, rgba))
}

/// Crop a region out of a frame. Returns an empty frame if the rect is outside.
pub fn crop(frame: &Frame, roi: Rect) -> Frame {
    let w = frame.width;
    let h = frame.height;
    if roi.w == 0 || roi.h == 0 || roi.x >= w || roi.y >= h {
        return Frame::new(0, 0, Vec::new());
    }
    let xe = roi.x.saturating_add(roi.w).min(w);
    let ye = roi.y.saturating_add(roi.h).min(h);
    let cw = xe - roi.x;
    let ch = ye - roi.y;
    let mut out = Vec::with_capacity((cw * ch * 4) as usize);
    for row in roi.y..ye {
        let row_start = (row * w + roi.x) as usize * 4;
        let row_end = (row * w + xe) as usize * 4;
        out.extend_from_slice(&frame.rgba[row_start..row_end]);
    }
    Frame::new(cw, ch, out)
}
