"""Squad panel reader — splits the squad strip into 3 rows and runs
:class:`LegendIconMatcher` on each.

The squad panel in Apex shows a vertical column of up to three rows: the
local player at the top, then teammates. Each row contains a small portrait
plus a name/health bar. We carve the panel into three equal horizontal
bands, take the leftmost ~50% of each (where the portrait sits), and feed
that to :class:`LegendIconMatcher`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from apex_coach.config.regions import HudLayout
from apex_coach.state.models import SquadMember
from apex_coach.utils.geometry import FractionalRect
from apex_coach.utils.logging import get_logger
from apex_coach.vision.legend_icons import LegendIconMatcher

_log = get_logger("squad-panel")


# Fraction of each row width that contains the portrait. The rest is
# nameplate / health bar.
PORTRAIT_WIDTH_FRACTION = 0.45
# Number of vertical slots we read. Apex has up to 3 squadmates.
NUM_SLOTS = 3


@dataclass(frozen=True, slots=True)
class SquadPanelResult:
    """Per-slot detection output."""

    members: tuple[SquadMember, ...]
    scores: tuple[float | None, ...]  # parallel to ``members``


class SquadPanelReader:
    """Read the squad strip; one call per captured frame."""

    def __init__(self, layout: HudLayout, matcher: LegendIconMatcher) -> None:
        self._layout = layout
        self._matcher = matcher

    def read(self, frame: np.ndarray) -> SquadPanelResult:
        if frame is None or frame.size == 0:
            return SquadPanelResult(members=(), scores=())

        h, w = frame.shape[:2]
        panel_rect = self._layout.squad_panel.to_pixels(w, h)
        x1 = max(0, panel_rect.x)
        y1 = max(0, panel_rect.y)
        x2 = min(w, panel_rect.x + panel_rect.w)
        y2 = min(h, panel_rect.y + panel_rect.h)
        if x2 <= x1 or y2 <= y1:
            return SquadPanelResult(members=(), scores=())

        panel = frame[y1:y2, x1:x2]
        if panel.size == 0:
            return SquadPanelResult(members=(), scores=())

        panel_h, panel_w = panel.shape[:2]
        row_h = panel_h // NUM_SLOTS
        portrait_w = int(panel_w * PORTRAIT_WIDTH_FRACTION)
        if row_h <= 0 or portrait_w <= 0:
            return SquadPanelResult(members=(), scores=())

        members: list[SquadMember] = []
        scores: list[float | None] = []
        for slot in range(NUM_SLOTS):
            top = slot * row_h
            bottom = top + row_h
            portrait = panel[top:bottom, 0:portrait_w]
            result = self._matcher.match(portrait)
            slug: str | None = None
            score: float | None = None
            if result is not None:
                slug, score = result
            members.append(SquadMember(slot=slot, alive=True, knocked=False, legend_slug=slug))
            scores.append(score)

        return SquadPanelResult(members=tuple(members), scores=tuple(scores))

    @staticmethod
    def portrait_rect_for_slot(layout: HudLayout, slot: int) -> FractionalRect:
        """Helper for the calibration wizard; returns the fractional rect of
        the slot's portrait inside the panel. ``slot`` must be in ``range(3)``.
        """
        if slot not in range(NUM_SLOTS):
            raise ValueError(f"slot must be 0..{NUM_SLOTS - 1}, got {slot}")
        p = layout.squad_panel
        row_h = p.h / NUM_SLOTS
        return FractionalRect(
            x=p.x,
            y=p.y + row_h * slot,
            w=p.w * PORTRAIT_WIDTH_FRACTION,
            h=row_h,
        )
