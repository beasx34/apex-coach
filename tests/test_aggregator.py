"""Tests for :class:`StateAggregator` smoothing + event emission."""

from __future__ import annotations

from apex_coach.state.aggregator import StateAggregator
from apex_coach.state.events import EventBus
from apex_coach.state.models import (
    GameEvent,
    GameEventInstance,
    GameState,
    KillFeedEvent,
    PlayerHud,
    RingState,
    ShieldTier,
    SquadMember,
    SquadState,
    Weapon,
    WeaponType,
)


class _Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[GameEvent, str | None]] = []

    def handler(self, event: GameEvent):  # type: ignore[no-untyped-def]
        def _h(_state: GameState, instance: GameEventInstance) -> None:
            self.events.append((event, instance.payload))

        return _h


def _new_bus_and_recorder() -> tuple[EventBus, _Recorder]:
    bus = EventBus()
    rec = _Recorder()
    for ev in GameEvent:
        bus.subscribe(ev, rec.handler(ev))
    return bus, rec


def test_hp_smoothing_with_median() -> None:
    bus, _ = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    # Two normal reads followed by a single-frame OCR glitch.
    for hp in (90, 88, 5):
        agg.update(PlayerHud(hp=hp))
    # Median of (90, 88, 5) is 88 — single bad sample is rejected.
    assert agg.state.player.hp == 88


def test_emits_low_hp_once_per_window() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    for hp in (30, 30, 30):
        agg.update(PlayerHud(hp=hp))
    low_hp_events = [e for e, _ in rec.events if e == GameEvent.LOW_HP]
    assert len(low_hp_events) == 1


def test_emits_shield_broken_on_falling_edge() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    # Fill the smoothing window with a non-zero shield first…
    for _ in range(3):
        agg.update(PlayerHud(hp=100, shield=50, shield_tier=ShieldTier.WHITE))
    # …then drain it to zero so the median actually drops to 0.
    for _ in range(3):
        agg.update(PlayerHud(hp=80, shield=0, shield_tier=ShieldTier.WHITE))
    assert any(e == GameEvent.SHIELD_BROKEN for e, _ in rec.events)


def test_emits_low_ammo_for_smg() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    weapon = Weapon(name="R-99", kind=WeaponType.SMG)
    # SMG threshold = 8 → 5 mag triggers low ammo.
    for _ in range(3):
        agg.update(PlayerHud(ammo_in_mag=5, weapon_primary=weapon))
    low_ammo = [e for e, _ in rec.events if e == GameEvent.LOW_AMMO]
    assert len(low_ammo) == 1


def test_emits_out_of_ammo() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    weapon = Weapon(name="R-99", kind=WeaponType.SMG)
    for _ in range(3):
        agg.update(PlayerHud(ammo_in_mag=0, weapon_primary=weapon))
    assert any(e == GameEvent.OUT_OF_AMMO for e, _ in rec.events)


def test_emits_ult_ready_on_rising_edge() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    agg.update(PlayerHud(ult_pct=0.5))
    agg.update(PlayerHud(ult_pct=1.0))
    assert any(e == GameEvent.ULTIMATE_READY for e, _ in rec.events)


def test_emits_teammate_knocked() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    squad_alive = SquadState(members=(SquadMember(slot=0, alive=True, knocked=False),))
    squad_knocked = SquadState(members=(SquadMember(slot=0, alive=True, knocked=True),))
    agg.update(PlayerHud(), squad=squad_alive)
    agg.update(PlayerHud(), squad=squad_knocked)
    knocked = [e for e, _ in rec.events if e == GameEvent.TEAMMATE_KNOCKED]
    assert len(knocked) == 1


def test_emits_ring_closing_soon_once() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    agg.update(PlayerHud(), ring=RingState(seconds_to_close=90, closing=True, inside=True))
    agg.update(PlayerHud(), ring=RingState(seconds_to_close=20, closing=True, inside=True))
    agg.update(PlayerHud(), ring=RingState(seconds_to_close=15, closing=True, inside=True))
    closing = [e for e, _ in rec.events if e == GameEvent.RING_CLOSING_SOON]
    assert len(closing) == 1


def test_emits_third_party_risk_from_kill_feed() -> None:
    bus, rec = _new_bus_and_recorder()
    agg = StateAggregator(bus)
    near = KillFeedEvent(
        raw="FOO killed BAR",
        killer="FOO",
        victim="BAR",
        weapon=None,
        knockdown_only=False,
        near_us=True,
    )
    agg.update(PlayerHud(), kill_events=[near])
    assert any(e == GameEvent.THIRD_PARTY_RISK for e, _ in rec.events)
