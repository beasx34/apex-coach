"""Tests for :class:`RulesEngine` — verifies each rule pushes the right tip."""

from __future__ import annotations

from apex_coach.state.events import EventBus
from apex_coach.state.models import (
    GameEvent,
    GameState,
    MatchPhase,
    PlayerHud,
    RingState,
    Weapon,
    WeaponType,
)
from apex_coach.tactics.rules import RulesEngine, Tip, TipPriority, TipSink


class _ListSink(TipSink):
    def __init__(self) -> None:
        self.tips: list[Tip] = []

    def push(self, tip: Tip) -> None:
        self.tips.append(tip)


def _state_with(**overrides: object) -> GameState:
    hud_kwargs: dict[str, object] = overrides.pop("hud", {})  # type: ignore[assignment]
    ring_kwargs: dict[str, object] = overrides.pop("ring", {})  # type: ignore[assignment]
    state = GameState(
        player=PlayerHud(**hud_kwargs),  # type: ignore[arg-type]
        ring=RingState(**ring_kwargs),  # type: ignore[arg-type]
    )
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def test_low_hp_emits_critical_tip() -> None:
    bus = EventBus()
    sink = _ListSink()
    RulesEngine(bus=bus, sink=sink)
    state = _state_with(hud={"hp": 25})
    bus.emit(GameEvent.LOW_HP, state)
    assert len(sink.tips) == 1
    tip = sink.tips[0]
    assert tip.priority == TipPriority.CRITICAL
    assert "хились" in tip.text.lower()


def test_low_ammo_uses_weapon_class_label() -> None:
    bus = EventBus()
    sink = _ListSink()
    RulesEngine(bus=bus, sink=sink)
    state = _state_with(
        hud={
            "ammo_in_mag": 4,
            "weapon_primary": Weapon(name="R-99", kind=WeaponType.SMG),
        }
    )
    bus.emit(GameEvent.LOW_AMMO, state)
    assert any("ПП" in t.text for t in sink.tips)


def test_shield_broken_pushes_high_priority_tip() -> None:
    bus = EventBus()
    sink = _ListSink()
    RulesEngine(bus=bus, sink=sink)
    bus.emit(GameEvent.SHIELD_BROKEN, _state_with())
    assert sink.tips and sink.tips[0].priority == TipPriority.HIGH


def test_outside_ring_is_critical() -> None:
    bus = EventBus()
    sink = _ListSink()
    RulesEngine(bus=bus, sink=sink)
    bus.emit(GameEvent.OUTSIDE_RING, _state_with())
    assert sink.tips and sink.tips[0].priority == TipPriority.CRITICAL


def test_teammate_knocked_endgame_says_kill_first() -> None:
    bus = EventBus()
    sink = _ListSink()
    RulesEngine(bus=bus, sink=sink)
    state = _state_with()
    state.match_phase = MatchPhase.ENDGAME
    bus.emit(GameEvent.TEAMMATE_KNOCKED, state)
    assert sink.tips and "добей" in sink.tips[0].text.lower()


def test_ult_ready_uses_legend_specific_tip() -> None:
    bus = EventBus()
    sink = _ListSink()
    engine = RulesEngine(bus=bus, sink=sink, current_legend="wraith")
    bus.emit(GameEvent.ULTIMATE_READY, _state_with())
    assert sink.tips and "портал" in sink.tips[0].text.lower()
    # And the slug can be updated mid-match.
    engine.set_legend("bangalore")
    bus.emit(GameEvent.ULTIMATE_READY, _state_with())
    assert "отход" in sink.tips[-1].text.lower() or "пуш" in sink.tips[-1].text.lower()
