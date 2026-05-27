"""Screen capture using mss.

Strict policy: we ONLY read the screen. We never read game memory, attach a
debugger, inject a DLL, or hook the renderer. This keeps us in the same
category as Discord overlay and OBS.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import numpy as np

from apex_coach.utils.geometry import Rect
from apex_coach.utils.logging import get_logger

_log = get_logger("capture")


@dataclass(slots=True)
class Frame:
    """A captured frame plus the monotonic timestamp it was grabbed at."""

    bgra: np.ndarray  # (H, W, 4)
    width: int
    height: int
    timestamp: float


class ScreenGrabber:
    """Thin asynchronous wrapper around ``mss.mss``.

    mss is itself synchronous and blocking. We call it on the asyncio default
    executor so the event loop stays responsive (~5 ms per 1080p grab).
    """

    def __init__(self, monitor: int = 1, target_fps: float = 10.0) -> None:
        if target_fps <= 0:
            raise ValueError("target_fps must be positive")
        self._monitor_idx = monitor
        self._interval = 1.0 / target_fps
        self._sct: Any = None  # lazy: avoid X server contact at import time
        self._monitor: dict[str, int] | None = None

    def _ensure_sct(self) -> tuple[Any, dict[str, int]]:
        if self._sct is None:
            import mss  # local import keeps the rest testable without an X server

            self._sct = mss.mss()
            monitors = self._sct.monitors
            if self._monitor_idx >= len(monitors):
                raise IndexError(
                    f"Monitor {self._monitor_idx} not found (have {len(monitors) - 1})"
                )
            self._monitor = monitors[self._monitor_idx]
            _log.info("Capturing monitor %d: %s", self._monitor_idx, self._monitor)
        assert self._monitor is not None
        return self._sct, self._monitor

    def grab(self) -> Frame:
        """Synchronously grab the full configured monitor."""
        sct, mon = self._ensure_sct()
        raw = sct.grab(mon)
        arr = np.asarray(raw, dtype=np.uint8)  # BGRA
        return Frame(bgra=arr, width=arr.shape[1], height=arr.shape[0], timestamp=time.monotonic())

    def grab_region(self, rect: Rect) -> np.ndarray:
        """Grab a sub-rectangle. Coordinates are absolute screen pixels."""
        sct, mon = self._ensure_sct()
        roi = {
            "left": mon["left"] + rect.x,
            "top": mon["top"] + rect.y,
            "width": rect.w,
            "height": rect.h,
        }
        raw = sct.grab(roi)
        return np.asarray(raw, dtype=np.uint8)

    async def stream(self) -> AsyncIterator[Frame]:
        """Yield frames at roughly ``target_fps``.

        Sleeps to absorb jitter — if a grab is slow, we skip the sleep so we
        don't accumulate lag.
        """
        loop = asyncio.get_running_loop()
        next_deadline = time.monotonic()
        while True:
            frame = await loop.run_in_executor(None, self.grab)
            yield frame
            next_deadline += self._interval
            sleep_for = next_deadline - time.monotonic()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                # Fell behind — reset the deadline to "now" so we don't burn CPU
                # trying to catch up.
                next_deadline = time.monotonic()

    def close(self) -> None:
        if self._sct is not None:
            self._sct.close()
            self._sct = None
