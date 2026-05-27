"""Minimap reader.

Currently extracts only a coarse "ring direction" hint by finding the dominant
storm-edge color in the minimap ROI and computing its centroid relative to the
ROI center. The result is converted to one of eight compass labels (N, NE, …).

This is intentionally simple — it's good enough for "rotate north-east" style
advice. A future PR can swap in a proper segmentation model.
"""

from __future__ import annotations

import cv2
import numpy as np

from apex_coach.config.regions import HudLayout
from apex_coach.state.models import MinimapSnapshot

_COMPASS = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")


class MinimapReader:
    def __init__(self, layout: HudLayout) -> None:
        self._layout = layout

    def read(self, frame: np.ndarray) -> MinimapSnapshot:
        h, w = frame.shape[:2]
        rect = self._layout.minimap.to_pixels(w, h)
        roi = frame[rect.y : rect.bottom, rect.x : rect.right]
        if roi.size == 0:
            return MinimapSnapshot()
        if roi.ndim == 3 and roi.shape[2] == 4:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
        direction = _ring_direction(roi)
        return MinimapSnapshot(ring_direction=direction, visible_enemy_pings=0)


def _ring_direction(roi: np.ndarray) -> str | None:
    """Return a compass label for the dominant storm edge, or ``None``."""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Storm ring is rendered as an orange/red ring on the minimap; the exact
    # color shifts between ring stages but the hue range is roughly 0..15 or 150..180.
    lower1 = np.array([0, 80, 80])
    upper1 = np.array([15, 255, 255])
    lower2 = np.array([160, 80, 80])
    upper2 = np.array([180, 255, 255])
    mask = cv2.bitwise_or(cv2.inRange(hsv, lower1, upper1), cv2.inRange(hsv, lower2, upper2))
    if cv2.countNonZero(mask) < 20:
        return None
    moments = cv2.moments(mask, binaryImage=True)
    if moments["m00"] <= 0:
        return None
    cx = moments["m10"] / moments["m00"]
    cy = moments["m01"] / moments["m00"]
    h, w = mask.shape
    dx = cx - w / 2
    dy = (h / 2) - cy  # invert so "up" is positive
    angle = np.degrees(np.arctan2(dy, dx))
    if angle < 0:
        angle += 360
    idx = int(((angle + 22.5) % 360) // 45)
    return _COMPASS[idx]
