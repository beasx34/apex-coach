"""Tests for :mod:`apex_coach.vision.legend_icons` and the squad reader."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from apex_coach.config.regions import LAYOUT_DEFAULT
from apex_coach.state.events import EventBus
from apex_coach.state.models import GameEvent, SquadMember, SquadState
from apex_coach.vision.legend_icons import ICON_SIZE, LegendIconMatcher
from apex_coach.vision.squad_panel import (
    NUM_SLOTS,
    PORTRAIT_WIDTH_FRACTION,
    SquadPanelReader,
)

# --- helpers ----------------------------------------------------------------


def _checkerboard(seed: int) -> np.ndarray:
    """Synthetic deterministic 64x64 grayscale icon that differs per slug."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(64, 64), dtype=np.uint8)


def _build_templates_dir(tmp_path: Path, slugs: list[str]) -> Path:
    icons_dir = tmp_path / "legend_icons"
    icons_dir.mkdir()
    for i, slug in enumerate(slugs):
        cv2.imwrite(str(icons_dir / f"{slug}.png"), _checkerboard(seed=i + 1))
    return icons_dir


# --- LegendIconMatcher ------------------------------------------------------


def test_matcher_with_no_templates_dir_disables_silently(tmp_path: Path) -> None:
    matcher = LegendIconMatcher(tmp_path / "does-not-exist")
    assert list(matcher.known_slugs()) == []
    assert matcher.match(_checkerboard(seed=1)) is None


def test_matcher_returns_best_slug_for_known_icon(tmp_path: Path) -> None:
    slugs = ["wraith", "octane", "bangalore"]
    icons_dir = _build_templates_dir(tmp_path, slugs)
    matcher = LegendIconMatcher(icons_dir)

    for i, slug in enumerate(slugs):
        # Feed back the same template (resized to a different size — matcher
        # normalizes) and expect to recover the slug.
        candidate = cv2.resize(_checkerboard(seed=i + 1), (96, 96))
        result = matcher.match(candidate)
        assert result is not None, f"matcher returned None for {slug}"
        assert result[0] == slug, f"expected {slug}, got {result[0]}"
        assert result[1] > 0.9, f"expected near-perfect score, got {result[1]:.3f}"


def test_matcher_below_threshold_returns_none(tmp_path: Path) -> None:
    icons_dir = _build_templates_dir(tmp_path, ["wraith"])
    matcher = LegendIconMatcher(icons_dir, min_score=0.95)
    # Pure-noise candidate should never beat 0.95 against a fixed template.
    rng = np.random.default_rng(999)
    noise = rng.integers(0, 256, size=(ICON_SIZE, ICON_SIZE), dtype=np.uint8)
    assert matcher.match(noise) is None


def test_matcher_handles_unknown_slug_files(tmp_path: Path) -> None:
    """Files for slugs we don't know about must be ignored."""
    icons_dir = tmp_path / "legend_icons"
    icons_dir.mkdir()
    cv2.imwrite(str(icons_dir / "imaginarius.png"), _checkerboard(seed=42))
    matcher = LegendIconMatcher(icons_dir)
    assert list(matcher.known_slugs()) == []


# --- SquadPanelReader -------------------------------------------------------


def test_squad_panel_returns_three_slots_with_empty_match(tmp_path: Path) -> None:
    matcher = LegendIconMatcher(tmp_path / "missing")
    reader = SquadPanelReader(LAYOUT_DEFAULT, matcher)
    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    result = reader.read(frame)
    assert len(result.members) == NUM_SLOTS
    assert all(m.legend_slug is None for m in result.members)


def test_squad_panel_recognises_planted_icons(tmp_path: Path) -> None:
    slugs = ["wraith", "octane", "bangalore"]
    icons_dir = _build_templates_dir(tmp_path, slugs)
    matcher = LegendIconMatcher(icons_dir)
    reader = SquadPanelReader(LAYOUT_DEFAULT, matcher)

    # Place templates in the layout's squad panel region.
    h, w = 1080, 1920
    frame = np.full((h, w, 3), 30, dtype=np.uint8)
    panel = LAYOUT_DEFAULT.squad_panel.to_pixels(w, h)
    row_h = panel.h // NUM_SLOTS
    portrait_w = int(panel.w * PORTRAIT_WIDTH_FRACTION)
    for i, _slug in enumerate(slugs):
        tile = cv2.resize(_checkerboard(seed=i + 1), (portrait_w, row_h))
        tile_bgr = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
        y0 = panel.y + i * row_h
        x0 = panel.x
        frame[y0 : y0 + row_h, x0 : x0 + portrait_w] = tile_bgr

    result = reader.read(frame)
    recovered = [m.legend_slug for m in result.members]
    assert recovered == slugs, f"unexpected: {recovered}"


def test_portrait_rect_for_slot_validates_input() -> None:
    with pytest.raises(ValueError):
        SquadPanelReader.portrait_rect_for_slot(LAYOUT_DEFAULT, 3)


def test_portrait_rect_for_slot_returns_expected_geometry() -> None:
    rect0 = SquadPanelReader.portrait_rect_for_slot(LAYOUT_DEFAULT, 0)
    rect2 = SquadPanelReader.portrait_rect_for_slot(LAYOUT_DEFAULT, 2)
    panel = LAYOUT_DEFAULT.squad_panel
    assert rect0.x == panel.x
    assert rect0.y == panel.y
    assert rect2.y > rect0.y
    assert abs(rect0.w - panel.w * PORTRAIT_WIDTH_FRACTION) < 1e-9


# --- Aggregator integration -------------------------------------------------


def test_aggregator_emits_legend_detected_event() -> None:
    from apex_coach.state.aggregator import StateAggregator
    from apex_coach.state.models import PlayerHud

    bus = EventBus()
    seen: list[tuple[GameEvent, str | None]] = []
    bus.subscribe(
        GameEvent.LEGEND_DETECTED,
        lambda _state, ev: seen.append((ev.event, ev.payload)),
    )
    agg = StateAggregator(bus=bus)

    agg.update(
        PlayerHud(),
        squad=SquadState(
            members=(
                SquadMember(slot=0, alive=True, knocked=False, legend_slug=None),
                SquadMember(slot=1, alive=True, knocked=False, legend_slug=None),
                SquadMember(slot=2, alive=True, knocked=False, legend_slug=None),
            )
        ),
    )
    assert seen == []

    agg.update(
        PlayerHud(),
        squad=SquadState(
            members=(
                SquadMember(slot=0, alive=True, knocked=False, legend_slug="wraith"),
                SquadMember(slot=1, alive=True, knocked=False, legend_slug=None),
                SquadMember(slot=2, alive=True, knocked=False, legend_slug="octane"),
            )
        ),
    )
    payloads = sorted(payload for _ev, payload in seen if payload is not None)
    assert payloads == ["0:wraith", "2:octane"]

    # Same legends again -> no duplicate emit.
    seen.clear()
    agg.update(
        PlayerHud(),
        squad=SquadState(
            members=(
                SquadMember(slot=0, alive=True, knocked=False, legend_slug="wraith"),
                SquadMember(slot=1, alive=True, knocked=False, legend_slug=None),
                SquadMember(slot=2, alive=True, knocked=False, legend_slug="octane"),
            )
        ),
    )
    assert seen == []
