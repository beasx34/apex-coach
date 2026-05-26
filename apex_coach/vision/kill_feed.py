"""Kill feed reader.

The kill feed lives in the top-right corner. Each row is a short string with
a killer name, a weapon icon, and a victim name. We OCR the whole region and
dedupe entries we've already seen using a rolling hash window — the same kill
typically lingers on screen for ~5 seconds across many frames.
"""

from __future__ import annotations

import re
import time
from collections import deque

import cv2
import numpy as np

from apex_coach.config.regions import HudLayout
from apex_coach.state.models import KillFeedEvent
from apex_coach.utils.logging import get_logger
from apex_coach.vision.ocr import OcrEngine

_log = get_logger("killfeed")

# A typical Apex kill-feed line looks like:
#   "PLAYERONE <icon> PLAYERTWO"
# We approximate the icon with whitespace after OCR strips it.
_LINE_PATTERN = re.compile(r"^\s*(?P<killer>[^\s].*?)\s{2,}(?P<victim>[^\s].*?)\s*$")
# Tags surfacing the "yourself" indicator vary by language; we keep the most
# common ones. Custom locales can be added without breaking the matcher.
_SELF_MARKERS = {"YOU", "ВЫ", "ТЫ"}


class KillFeedReader:
    """Parses the kill-feed ROI and yields new :class:`KillFeedEvent`s."""

    def __init__(self, layout: HudLayout, ocr: OcrEngine, dedup_window: int = 32) -> None:
        self._layout = layout
        self._ocr = ocr
        self._seen: deque[str] = deque(maxlen=dedup_window)

    def read(self, frame: np.ndarray) -> list[KillFeedEvent]:
        h, w = frame.shape[:2]
        rect = self._layout.kill_feed.to_pixels(w, h)
        roi = frame[rect.y : rect.bottom, rect.x : rect.right]
        if roi.size == 0:
            return []
        if roi.ndim == 3 and roi.shape[2] == 4:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        results = self._ocr.read_text(roi)
        new_events: list[KillFeedEvent] = []
        now = time.monotonic()
        for r in results:
            line = r.text.strip()
            if not line or r.confidence < 0.45:
                continue
            if line in self._seen:
                continue
            self._seen.append(line)
            new_events.append(_parse_line(line, now))
        return new_events


def _parse_line(line: str, ts: float) -> KillFeedEvent:
    """Turn a single kill-feed line into a :class:`KillFeedEvent`.

    OCR text quality is uneven so we keep parsing lenient — when we can't pick
    out names cleanly, we still emit an event with ``raw`` set so downstream
    consumers (the AI coach) can read it verbatim.
    """
    knockdown_only = "knock" in line.lower() or "нокд" in line.lower()
    near_us = any(marker in line.upper() for marker in _SELF_MARKERS)
    m = _LINE_PATTERN.match(line)
    killer: str | None
    victim: str | None
    if m:
        killer = m.group("killer").strip()
        victim = m.group("victim").strip()
    else:
        killer = victim = None
    return KillFeedEvent(
        raw=line,
        killer=killer,
        victim=victim,
        weapon=None,
        knockdown_only=knockdown_only,
        near_us=near_us,
        timestamp=ts,
    )
