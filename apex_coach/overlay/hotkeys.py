"""Global hotkeys via pynput.

pynput's ``GlobalHotKeys`` runs a background thread. Callbacks fire on that
thread, so anything Qt-touching must be marshalled to the GUI thread by the
caller (:class:`QMetaObject.invokeMethod` or a signal). Our callers schedule
calls on the asyncio loop, which is fine because none of them touch Qt
directly.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from apex_coach.config.settings import HotkeySettings
from apex_coach.utils.logging import get_logger

_log = get_logger("hotkeys")


class HotkeyManager:
    """Wraps :class:`pynput.keyboard.GlobalHotKeys`. Idempotent start/stop."""

    def __init__(
        self,
        settings: HotkeySettings,
        *,
        on_ai_request: Callable[[], None],
        on_toggle: Callable[[], None],
        on_calibrate: Callable[[], None],
    ) -> None:
        self._settings = settings
        self._callbacks = {
            settings.ai_request: on_ai_request,
            settings.toggle: on_toggle,
            settings.calibrate: on_calibrate,
        }
        self._listener: Any = None

    def start(self) -> None:
        if self._listener is not None:
            return
        try:
            from pynput.keyboard import GlobalHotKeys
        except Exception:  # pragma: no cover — pynput is optional on Linux CI
            _log.warning("pynput unavailable — hotkeys disabled.")
            return
        try:
            listener = GlobalHotKeys(self._callbacks)
            listener.start()
            self._listener = listener
        except Exception:  # pragma: no cover — env-dependent
            _log.warning("Could not register global hotkeys (need accessibility perms?).")
            self._listener = None

    def stop(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is None:
            return
        with contextlib.suppress(Exception):  # pragma: no cover — best-effort
            listener.stop()
