"""Verifies the LLM prompt renders without errors and contains key fields."""

from __future__ import annotations

from apex_coach.ai.prompts import SYSTEM_PROMPT_RU, build_user_prompt
from apex_coach.state.models import (
    GameState,
    MatchPhase,
    PlayerHud,
    RingState,
    ShieldTier,
    Weapon,
    WeaponType,
)


def test_system_prompt_has_meta_placeholder() -> None:
    assert "{meta_notes}" in SYSTEM_PROMPT_RU


def test_user_prompt_renders_complete_state() -> None:
    state = GameState(
        player=PlayerHud(
            hp=80,
            shield=50,
            shield_tier=ShieldTier.WHITE,
            ammo_in_mag=12,
            ammo_reserve=80,
            weapon_primary=Weapon(name="R-301", kind=WeaponType.AR),
            weapon_secondary=None,
            ability_cd_s=0.0,
            ult_pct=0.7,
        ),
        ring=RingState(seconds_to_close=45.0, closing=True, inside=True),
        match_phase=MatchPhase.MID,
    )
    text = build_user_prompt(state, legend="wraith")
    assert "wraith" in text.lower() or "wr" in text.lower()
    assert "R-301" in text
    # Mid phase comes through as a label in the rendered prompt.
    assert "mid" in text.lower()
    assert "45с" in text
