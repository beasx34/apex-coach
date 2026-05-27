"""Sanity tests for :mod:`apex_coach.tactics.knowledge`."""

from __future__ import annotations

import pytest

from apex_coach.state.models import WeaponType
from apex_coach.tactics.knowledge import (
    LEGEND_KB,
    WEAPON_CLASS_RU,
    LegendRole,
    lookup_legend,
)

# Slugs we promise to support — caught at PR time so accidental deletions fail loudly.
_REQUIRED_SLUGS = frozenset(
    {
        "bloodhound",
        "gibraltar",
        "lifeline",
        "pathfinder",
        "wraith",
        "bangalore",
        "caustic",
        "mirage",
        "octane",
        "wattson",
        "crypto",
        "revenant",
        "loba",
        "rampart",
        "horizon",
        "fuse",
        "valkyrie",
        "seer",
        "ash",
        "maggie",
        "newcastle",
        "vantage",
        "catalyst",
        "ballistic",
        "conduit",
        "alter",
        "sparrow",
    }
)


def test_required_legends_present() -> None:
    missing = _REQUIRED_SLUGS - set(LEGEND_KB)
    assert not missing, f"Missing legends: {sorted(missing)}"


@pytest.mark.parametrize("slug", sorted(_REQUIRED_SLUGS))
def test_each_legend_has_russian_name_and_tip(slug: str) -> None:
    info = LEGEND_KB[slug]
    # Name must be at least one cyrillic character — accidental English copy-paste fails.
    assert any("\u0400" <= ch <= "\u04ff" for ch in info.name), f"Non-cyrillic name for {slug!r}"
    assert info.tactical_ult_tip_ru.strip(), f"Empty ult tip for {slug!r}"
    assert isinstance(info.role, LegendRole)


def test_lookup_legend_is_case_insensitive() -> None:
    assert lookup_legend("WrAiTh") is LEGEND_KB["wraith"]
    assert lookup_legend("unknown-legend-slug") is None


def test_weapon_class_dict_covers_all_known_types() -> None:
    missing = set(WeaponType) - set(WEAPON_CLASS_RU)
    assert not missing, f"Missing weapon class labels for: {sorted(t.name for t in missing)}"
