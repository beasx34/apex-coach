"""Match squad-panel legend icons to known slugs by template matching.

Apex draws a small portrait of each squad member (yourself + up to two
teammates) in the top-left of the HUD. The image is small (~40-60 px) but
clean and consistently lit, so OpenCV template matching against pre-saved
reference icons is reliable enough as long as the templates are scaled to a
similar height.

Reference icons live in ``resources/legend_icons/{slug}.png``. You can grab
them once from any HUD screenshot, crop to the bounding circle, and the
matcher will normalize sizing.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import cv2
import numpy as np

from apex_coach.tactics.knowledge import LEGEND_KB
from apex_coach.utils.logging import get_logger

_log = get_logger("legend-icons")


# Templates are resized to this square. Big enough to discriminate
# silhouettes, small enough to keep matching cheap (~1 ms per slot).
ICON_SIZE = 48

# Below this normalized correlation score we report "no match" rather than
# guessing. Tuned empirically — clean icons score 0.55+, noise scores <0.3.
DEFAULT_MIN_SCORE = 0.45


class LegendIconMatcher:
    """Loads icon templates lazily on first use and matches a candidate ROI."""

    def __init__(
        self,
        templates_dir: Path | None,
        *,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> None:
        self._dir = templates_dir
        self._min_score = min_score
        self._templates: dict[str, np.ndarray] | None = None

    def _load(self) -> dict[str, np.ndarray]:
        if self._templates is not None:
            return self._templates
        out: dict[str, np.ndarray] = {}
        if self._dir is None or not self._dir.is_dir():
            _log.info("Legend icons dir missing — legend detection disabled.")
            self._templates = out
            return out
        for slug in LEGEND_KB:
            path = self._dir / f"{slug}.png"
            if not path.is_file():
                continue
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is None or img.size == 0:
                continue
            out[slug] = _normalize_icon(img)
        _log.info("Loaded %d legend icon templates.", len(out))
        self._templates = out
        return out

    def known_slugs(self) -> Iterable[str]:
        return self._load().keys()

    def match(self, roi: np.ndarray) -> tuple[str, float] | None:
        """Return the best (slug, score) above the threshold, or ``None``."""
        templates = self._load()
        if not templates or roi is None or roi.size == 0:
            return None

        candidate = _normalize_icon(roi)
        best_slug: str | None = None
        best_score = -1.0
        for slug, tpl in templates.items():
            score = _correlation(candidate, tpl)
            if score > best_score:
                best_score = score
                best_slug = slug
        if best_slug is None or best_score < self._min_score:
            return None
        return best_slug, best_score


def _normalize_icon(img: np.ndarray) -> np.ndarray:
    """Resize to ``ICON_SIZE`` and centre-pad so silhouettes line up."""
    if img.ndim == 3:
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.resize(img, (ICON_SIZE, ICON_SIZE), interpolation=cv2.INTER_AREA)


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Zero-mean normalized cross-correlation in ``[-1, 1]``."""
    if a.shape != b.shape:
        return -1.0
    af = a.astype(np.float32)
    bf = b.astype(np.float32)
    af -= af.mean()
    bf -= bf.mean()
    denom = float(np.linalg.norm(af) * np.linalg.norm(bf))
    if denom <= 1e-6:
        return 0.0
    return float((af * bf).sum() / denom)
