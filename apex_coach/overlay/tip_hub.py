"""Tip queue with dedup and priority.

The overlay subscribes to :class:`TipHub` and listens for `tip_changed`. The
hub holds at most one "active" tip — newly pushed tips replace older ones only
if they are stricter (higher priority) or the active tip has expired.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from apex_coach.tactics.rules import Tip, TipSink
from apex_coach.utils.logging import get_logger

_log = get_logger("tip-hub")


# Window during which a duplicate (same text) tip is suppressed.
_DEDUP_WINDOW_S = 5.0


class TipHub(TipSink):
    """Routes tips from rules / AI to the overlay.

    Decoupled from PySide6 — the overlay just registers a callback.
    """

    def __init__(self) -> None:
        self._active: Tip | None = None
        self._active_until: float = 0.0
        self._last_pushed: dict[str, float] = {}
        self._listener: Callable[[Tip | None], None] | None = None

    def set_listener(self, listener: Callable[[Tip | None], None]) -> None:
        self._listener = listener

    def active_tip(self) -> Tip | None:
        if self._active is None:
            return None
        if time.monotonic() > self._active_until:
            return None
        return self._active

    # ------------------------------------------------------------------
    # TipSink protocol
    # ------------------------------------------------------------------
    def push(self, tip: Tip) -> None:
        now = time.monotonic()
        # Dedup
        last_ts = self._last_pushed.get(tip.text)
        if last_ts is not None and now - last_ts < _DEDUP_WINDOW_S:
            return
        self._last_pushed[tip.text] = now

        # Replace active only if new tip is at least as important, or the
        # active tip has expired.
        active = self.active_tip()
        if active is not None and tip.priority < active.priority:
            return

        self._active = tip
        self._active_until = now + tip.ttl_s
        if self._listener is not None:
            self._listener(tip)

    def tick(self) -> None:
        """Called periodically by the overlay so we can clear expired tips."""
        if self._active is None:
            return
        if time.monotonic() > self._active_until:
            self._active = None
            if self._listener is not None:
                self._listener(None)
