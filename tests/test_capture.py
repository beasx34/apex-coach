"""Capture-layer construction tests (does not require an X server)."""

from __future__ import annotations

import pytest

from apex_coach.capture.screen import ScreenGrabber


def test_grabber_rejects_zero_fps() -> None:
    with pytest.raises(ValueError):
        ScreenGrabber(monitor=1, target_fps=0.0)
