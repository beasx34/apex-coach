import type { HudRois, Rect } from "./types";

// Default ROIs assume a 1920x1080 game window. The UI lets the user override.
// Coordinates are absolute pixel rectangles (x, y, w, h).
export function defaultRois(width = 1920, height = 1080): HudRois {
  const ammo: Rect = {
    x: Math.round(width * 0.84),
    y: Math.round(height * 0.86),
    w: Math.round(width * 0.13),
    h: Math.round(height * 0.07),
  };
  const squads_left: Rect = {
    x: Math.round(width * 0.86),
    y: Math.round(height * 0.04),
    w: Math.round(width * 0.12),
    h: Math.round(height * 0.04),
  };
  const kills: Rect = {
    x: Math.round(width * 0.40),
    y: Math.round(height * 0.02),
    w: Math.round(width * 0.08),
    h: Math.round(height * 0.04),
  };
  const damage: Rect = {
    x: Math.round(width * 0.48),
    y: Math.round(height * 0.02),
    w: Math.round(width * 0.08),
    h: Math.round(height * 0.04),
  };
  const ring_timer: Rect = {
    x: Math.round(width * 0.46),
    y: Math.round(height * 0.05),
    w: Math.round(width * 0.08),
    h: Math.round(height * 0.04),
  };
  return { ammo, squads_left, kills, damage, ring_timer };
}
