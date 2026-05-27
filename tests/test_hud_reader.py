"""HudReader smoke tests — driven by tiny synthetic numpy frames."""

from __future__ import annotations

import numpy as np

from apex_coach.config.regions import LAYOUT_DEFAULT
from apex_coach.state.models import ShieldTier
from apex_coach.vision.digits import DigitMatcher
from apex_coach.vision.hud_reader import (
    HudReader,
    _classify_shield_color,
    _classify_weapon,
)
from apex_coach.vision.ocr import OcrEngine


class _StubOcr(OcrEngine):
    """OCR that returns a canned answer — no model load."""

    def __init__(self, answer: str | None = None) -> None:
        self._answer = answer

    def read_text(self, image: np.ndarray):  # type: ignore[override]
        return []

    def read_first_text(self, image: np.ndarray, *, min_confidence: float = 0.5) -> str | None:  # type: ignore[override]
        return self._answer


def _blank_frame() -> np.ndarray:
    return np.zeros((1080, 1920, 3), dtype=np.uint8)


def test_hud_reader_returns_none_when_no_templates() -> None:
    reader = HudReader(
        layout=LAYOUT_DEFAULT,
        digits=DigitMatcher(templates_dir=None),
        ocr=_StubOcr(),
    )
    hud = reader.read(_blank_frame())
    assert hud.hp is None
    assert hud.shield is None
    assert hud.ammo_in_mag is None


def test_classify_shield_color_picks_closest_tier() -> None:
    assert _classify_shield_color((230, 230, 230)) == ShieldTier.WHITE
    assert _classify_shield_color((60, 140, 230)) == ShieldTier.BLUE
    assert _classify_shield_color((170, 90, 220)) == ShieldTier.PURPLE
    assert _classify_shield_color((220, 60, 60)) == ShieldTier.RED
    # Very dark sample → treated as no shield.
    assert _classify_shield_color((5, 5, 5)) == ShieldTier.NONE


def test_classify_weapon_strict_and_fuzzy_match() -> None:
    weapon = _classify_weapon("R-301")
    assert weapon is not None and weapon.name == "R-301"
    # Spaces / dashes shouldn't matter.
    weapon = _classify_weapon("r 301")
    assert weapon is not None and weapon.name == "R-301"


def test_classify_weapon_unknown_returns_unknown_kind() -> None:
    weapon = _classify_weapon("MARSGUN-9000")
    assert weapon is not None
    assert weapon.name == "MARSGUN-9000"
    from apex_coach.state.models import WeaponType

    assert weapon.kind == WeaponType.UNKNOWN
