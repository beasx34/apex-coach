"""Fast digit recognition for HP / shield / ammo counters.

Apex Legends uses a stylized stencil-style font for HUD numerics. General-purpose
OCR has high error rates on it, so we ship our own digit recognizer:

1. Threshold the ROI to a binary image.
2. Find connected components.
3. For each component, normalize size and compare against per-digit templates
   shipped under ``resources/digit_templates/`` using normalized cross-correlation.

We deliberately avoid a learned model here — the digits are visually simple,
templates run in well under a millisecond, and we never need to ship a GPU.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from apex_coach.utils.logging import get_logger

_log = get_logger("digits")

DIGIT_HEIGHT = 32  # normalized template / glyph height in pixels


@dataclass(frozen=True, slots=True)
class _DigitTemplate:
    digit: int
    image: np.ndarray  # uint8, single channel, normalized to DIGIT_HEIGHT


class DigitMatcher:
    """Reads multi-digit base-10 numbers from a small ROI.

    Templates are loaded lazily on first ``read_number`` call. If no templates
    are available on disk (e.g. fresh checkout), the matcher falls back to
    returning ``None`` so the caller can gracefully degrade.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._templates_dir = templates_dir
        self._templates: list[_DigitTemplate] | None = None

    def _load_templates(self) -> list[_DigitTemplate]:
        if self._templates is not None:
            return self._templates
        templates: list[_DigitTemplate] = []
        directory = self._templates_dir
        if directory is None or not directory.is_dir():
            _log.warning(
                "No digit templates dir at %s — DigitMatcher will return None. "
                "Run the calibration wizard to capture per-resolution templates.",
                directory,
            )
            self._templates = []
            return self._templates
        for path in sorted(directory.glob("*.png")):
            stem = path.stem
            if not stem.isdigit():
                continue
            digit = int(stem)
            if not (0 <= digit <= 9):
                continue
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            img = _normalize_glyph(img)
            templates.append(_DigitTemplate(digit=digit, image=img))
        if not templates:
            _log.warning("Templates dir %s contains no recognizable digit PNGs.", directory)
        self._templates = templates
        return templates

    def read_number(self, image: np.ndarray, *, max_digits: int = 3) -> int | None:
        """Return the integer in the ROI, or ``None`` if it can't be read."""
        templates = self._load_templates()
        if not templates:
            return None
        glyphs = _segment_digits(image)
        if not glyphs:
            return None
        glyphs = glyphs[:max_digits]
        digits: list[int] = []
        for glyph in glyphs:
            best_score = -1.0
            best_digit = -1
            for tpl in templates:
                score = _match_score(glyph, tpl.image)
                if score > best_score:
                    best_score = score
                    best_digit = tpl.digit
            if best_score < 0.4 or best_digit < 0:
                # Low confidence — abort the whole read rather than guess.
                return None
            digits.append(best_digit)
        return int("".join(str(d) for d in digits))


# ---------------------------------------------------------------------------
# helpers (module-level so they're trivially unit-testable)
# ---------------------------------------------------------------------------


def _normalize_glyph(glyph: np.ndarray) -> np.ndarray:
    """Resize a single-digit grayscale glyph to a fixed height, preserving aspect."""
    if glyph.size == 0:
        return glyph
    h, w = glyph.shape[:2]
    if h == 0:
        return glyph
    scale = DIGIT_HEIGHT / h
    new_w = max(1, int(round(w * scale)))
    return cv2.resize(glyph, (new_w, DIGIT_HEIGHT), interpolation=cv2.INTER_AREA)


def _segment_digits(image: np.ndarray) -> list[np.ndarray]:
    """Split a grayscale ROI into individual digit images, left-to-right.

    Uses Otsu thresholding + connected components. Filters out specks and the
    occasional UI iconography that bleeds into the ROI.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    # Apex HUD digits are bright on dark backgrounds.
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    glyphs: list[tuple[int, np.ndarray]] = []
    img_h = binary.shape[0]
    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]
        if area < 6:
            continue
        if h < img_h * 0.35:
            # Too short to be a digit.
            continue
        crop = binary[y : y + h, x : x + w]
        glyphs.append((x, _normalize_glyph(crop)))
    glyphs.sort(key=lambda entry: entry[0])
    return [g for _x, g in glyphs]


def _match_score(glyph: np.ndarray, template: np.ndarray) -> float:
    """Normalized cross-correlation between a glyph and a template.

    Both inputs must be single-channel uint8 images at ``DIGIT_HEIGHT`` height.
    The wider of the two is letter-boxed onto the other so cv2.matchTemplate
    has a valid window.
    """
    if glyph.size == 0 or template.size == 0:
        return -1.0
    if glyph.shape[1] < template.shape[1]:
        glyph, template = template, glyph
    if glyph.shape[0] != template.shape[0]:
        return -1.0
    result = cv2.matchTemplate(glyph, template, cv2.TM_CCOEFF_NORMED)
    return float(result.max())
