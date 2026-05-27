"""Composite HUD reader.

Combines :class:`DigitMatcher` (for numeric counters) and :class:`OcrEngine`
(for weapon names) plus pixel-level color sampling for the shield tier.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from apex_coach.config.regions import HudLayout
from apex_coach.state.models import PlayerHud, ShieldTier, Weapon, WeaponType
from apex_coach.utils.geometry import FractionalRect
from apex_coach.utils.logging import get_logger
from apex_coach.vision.digits import DigitMatcher
from apex_coach.vision.ocr import OcrEngine

_log = get_logger("hud")


# Approximate RGB swatches for the four shield tiers. Sampled from
# reference screenshots; matched in LAB-space with Euclidean distance.
_SHIELD_TIER_SWATCHES: dict[ShieldTier, tuple[int, int, int]] = {
    ShieldTier.WHITE: (220, 220, 220),
    ShieldTier.BLUE: (60, 140, 230),
    ShieldTier.PURPLE: (170, 90, 220),
    ShieldTier.RED: (220, 60, 60),
}


@dataclass(frozen=True, slots=True)
class HudReaderConfig:
    """Knobs you might tune per resolution. Only the basics for the MVP."""

    weapon_ocr_min_confidence: float = 0.55


class HudReader:
    """High-level orchestrator: full screen frame → :class:`PlayerHud`."""

    def __init__(
        self,
        layout: HudLayout,
        digits: DigitMatcher,
        ocr: OcrEngine,
        config: HudReaderConfig | None = None,
    ) -> None:
        self._layout = layout
        self._digits = digits
        self._ocr = ocr
        self._config = config or HudReaderConfig()

    def read(self, frame: np.ndarray) -> PlayerHud:
        h, w = frame.shape[:2]

        hp = self._read_number(frame, self._layout.hp_value, w, h, max_digits=3)
        shield = self._read_number(frame, self._layout.shield_value, w, h, max_digits=3)
        ammo_mag = self._read_number(frame, self._layout.ammo_in_mag, w, h, max_digits=3)
        ammo_res = self._read_number(frame, self._layout.ammo_reserve, w, h, max_digits=3)

        tier = self._read_shield_tier(frame, w, h)
        weapon_primary = self._read_weapon(frame, self._layout.weapon_slot_1, w, h)
        weapon_secondary = self._read_weapon(frame, self._layout.weapon_slot_2, w, h)

        return PlayerHud(
            hp=hp,
            shield=shield,
            shield_tier=tier,
            ammo_in_mag=ammo_mag,
            ammo_reserve=ammo_res,
            weapon_primary=weapon_primary,
            weapon_secondary=weapon_secondary,
            ability_cd_s=None,  # populated by future enhancement
            ult_pct=None,  # populated by future enhancement
        )

    # ------------------------------------------------------------------
    # ROI helpers
    # ------------------------------------------------------------------
    def _crop(self, frame: np.ndarray, region: FractionalRect, w: int, h: int) -> np.ndarray:
        rect = region.to_pixels(w, h)
        x1 = max(0, rect.x)
        y1 = max(0, rect.y)
        x2 = min(w, rect.x + rect.w)
        y2 = min(h, rect.y + rect.h)
        if x2 <= x1 or y2 <= y1:
            return np.zeros((0, 0, frame.shape[2] if frame.ndim == 3 else 1), dtype=frame.dtype)
        return frame[y1:y2, x1:x2]

    def _read_number(
        self,
        frame: np.ndarray,
        region: FractionalRect,
        w: int,
        h: int,
        *,
        max_digits: int,
    ) -> int | None:
        roi = self._crop(frame, region, w, h)
        if roi.size == 0:
            return None
        gray = (
            cv2.cvtColor(roi, cv2.COLOR_BGRA2GRAY)
            if roi.ndim == 3 and roi.shape[2] == 4
            else (cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if roi.ndim == 3 else roi)
        )
        return self._digits.read_number(gray, max_digits=max_digits)

    def _read_shield_tier(self, frame: np.ndarray, w: int, h: int) -> ShieldTier:
        roi = self._crop(frame, self._layout.shield_bar, w, h)
        if roi.size == 0:
            return ShieldTier.NONE
        # Strip the alpha channel if present so we get a clean BGR sample.
        if roi.ndim == 3 and roi.shape[2] == 4:
            roi = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
        # Use the median color of the brightest 25 % of pixels — that biases
        # toward the bar itself rather than the dark border around it.
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mask = gray > np.quantile(gray, 0.75)
        if not mask.any():
            return ShieldTier.NONE
        sample_bgr = roi[mask].mean(axis=0)
        sample_rgb = (int(sample_bgr[2]), int(sample_bgr[1]), int(sample_bgr[0]))
        return _classify_shield_color(sample_rgb)

    def _read_weapon(
        self, frame: np.ndarray, region: FractionalRect, w: int, h: int
    ) -> Weapon | None:
        roi = self._crop(frame, region, w, h)
        if roi.size == 0:
            return None
        text = self._ocr.read_first_text(roi, min_confidence=self._config.weapon_ocr_min_confidence)
        if not text:
            return None
        return _classify_weapon(text)


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------


def _classify_shield_color(rgb: tuple[int, int, int]) -> ShieldTier:
    """Pick the closest tier swatch in (linear) RGB space."""
    best_tier = ShieldTier.NONE
    best_dist = float("inf")
    r, g, b = rgb
    for tier, (tr, tg, tb) in _SHIELD_TIER_SWATCHES.items():
        d = (tr - r) ** 2 + (tg - g) ** 2 + (tb - b) ** 2
        if d < best_dist:
            best_dist = d
            best_tier = tier
    # If the sampled pixel is essentially black/dark — assume no shield.
    if sum(rgb) < 60:
        return ShieldTier.NONE
    return best_tier


# Mapping of known Apex weapon names to a weapon class. Update on patches.
_WEAPON_TO_TYPE: dict[str, WeaponType] = {
    "R-301": WeaponType.AR,
    "R301": WeaponType.AR,
    "FLATLINE": WeaponType.AR,
    "HEMLOK": WeaponType.AR,
    "HAVOC": WeaponType.AR,
    "NEMESIS": WeaponType.AR,
    "R-99": WeaponType.SMG,
    "R99": WeaponType.SMG,
    "VOLT": WeaponType.SMG,
    "ALTERNATOR": WeaponType.SMG,
    "PROWLER": WeaponType.SMG,
    "CAR": WeaponType.SMG,
    "DEVOTION": WeaponType.LMG,
    "SPITFIRE": WeaponType.LMG,
    "RAMPAGE": WeaponType.LMG,
    "L-STAR": WeaponType.LMG,
    "G7": WeaponType.MARKSMAN,
    "G7 SCOUT": WeaponType.MARKSMAN,
    "30-30": WeaponType.MARKSMAN,
    "30-30 REPEATER": WeaponType.MARKSMAN,
    "TRIPLE TAKE": WeaponType.MARKSMAN,
    "BOCEK": WeaponType.MARKSMAN,
    "LONGBOW": WeaponType.SNIPER,
    "CHARGE RIFLE": WeaponType.SNIPER,
    "SENTINEL": WeaponType.SNIPER,
    "KRABER": WeaponType.SNIPER,
    "PEACEKEEPER": WeaponType.SHOTGUN,
    "MASTIFF": WeaponType.SHOTGUN,
    "EVA-8": WeaponType.SHOTGUN,
    "MOZAMBIQUE": WeaponType.SHOTGUN,
    "P2020": WeaponType.PISTOL,
    "RE-45": WeaponType.PISTOL,
    "WINGMAN": WeaponType.PISTOL,
}


def _classify_weapon(text: str) -> Weapon | None:
    """Look up a weapon name (case-insensitive, ignoring spacing) in the KB."""
    cleaned = text.upper().strip()
    if not cleaned:
        return None
    if cleaned in _WEAPON_TO_TYPE:
        return Weapon(name=cleaned, kind=_WEAPON_TO_TYPE[cleaned])
    # Try a relaxed match — sometimes OCR drops a dash or adds whitespace.
    compact = cleaned.replace("-", "").replace(" ", "")
    for key, kind in _WEAPON_TO_TYPE.items():
        if compact == key.replace("-", "").replace(" ", ""):
            return Weapon(name=key, kind=kind)
    return Weapon(name=cleaned, kind=WeaponType.UNKNOWN)
