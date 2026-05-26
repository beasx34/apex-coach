"""Aggregates per-frame HUD reads into a smoothed GameState and emits events."""

from __future__ import annotations

import statistics
import time
from collections import deque

from apex_coach.state.events import EventBus
from apex_coach.state.models import (
    GameEvent,
    GameState,
    KillFeedEvent,
    MatchPhase,
    MinimapSnapshot,
    PlayerHud,
    RingState,
    SquadState,
    WeaponType,
)

# Thresholds — tuned for typical play. Tweak in tactics/knowledge.py if needed.
LOW_HP_THRESHOLD = 40
LOW_AMMO_FRACTION = 0.30
RING_SOON_SECONDS = 30.0
THIRD_PARTY_WINDOW_S = 8.0


class StateAggregator:
    """Smooths OCR jitter and emits diff-based events.

    Smoothing is a 3-sample median on numeric fields. That kills single-frame
    OCR misreads without adding noticeable latency.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._state = GameState()
        self._hp_window: deque[int] = deque(maxlen=3)
        self._shield_window: deque[int] = deque(maxlen=3)
        self._ammo_window: deque[int] = deque(maxlen=3)
        self._last_low_hp_emit: float = 0.0
        self._last_low_ammo_emit: float = 0.0

    @property
    def state(self) -> GameState:
        return self._state

    def update(
        self,
        hud: PlayerHud,
        kill_events: list[KillFeedEvent] | None = None,
        minimap: MinimapSnapshot | None = None,
        ring: RingState | None = None,
        squad: SquadState | None = None,
    ) -> GameState:
        """Fold a fresh frame into the running state and emit events."""
        prev = self._state
        smoothed = self._smooth(hud)

        new_state = GameState(
            player=smoothed,
            squad=squad if squad is not None else prev.squad,
            ring=ring if ring is not None else prev.ring,
            minimap=minimap if minimap is not None else prev.minimap,
            recent_events=prev.recent_events,
            match_phase=_phase_from(prev.match_phase, ring),
            timestamp=time.monotonic(),
        )
        self._state = new_state

        self._emit_diff(prev, new_state, kill_events or [])
        return new_state

    # ------------------------------------------------------------------
    # smoothing
    # ------------------------------------------------------------------
    def _smooth(self, hud: PlayerHud) -> PlayerHud:
        if hud.hp is not None:
            self._hp_window.append(hud.hp)
        if hud.shield is not None:
            self._shield_window.append(hud.shield)
        if hud.ammo_in_mag is not None:
            self._ammo_window.append(hud.ammo_in_mag)

        return PlayerHud(
            hp=_median_or_none(self._hp_window),
            shield=_median_or_none(self._shield_window),
            shield_tier=hud.shield_tier,
            ammo_in_mag=_median_or_none(self._ammo_window),
            ammo_reserve=hud.ammo_reserve,
            weapon_primary=hud.weapon_primary,
            weapon_secondary=hud.weapon_secondary,
            ability_cd_s=hud.ability_cd_s,
            ult_pct=hud.ult_pct,
            timestamp=hud.timestamp,
        )

    # ------------------------------------------------------------------
    # diff -> events
    # ------------------------------------------------------------------
    def _emit_diff(
        self,
        prev: GameState,
        cur: GameState,
        kill_events: list[KillFeedEvent],
    ) -> None:
        bus = self._bus

        # Damage
        if (
            prev.player.hp is not None
            and cur.player.hp is not None
            and cur.player.hp < prev.player.hp
        ):
            bus.emit(GameEvent.TOOK_DAMAGE, cur, payload=f"{prev.player.hp}->{cur.player.hp}")

        # Shield broken
        if (
            prev.player.shield is not None
            and cur.player.shield is not None
            and prev.player.shield > 0
            and cur.player.shield == 0
        ):
            bus.emit(GameEvent.SHIELD_BROKEN, cur)

        # Low HP (throttled)
        if (
            cur.player.hp is not None
            and cur.player.hp <= LOW_HP_THRESHOLD
            and cur.timestamp - self._last_low_hp_emit > 4.0
        ):
            bus.emit(GameEvent.LOW_HP, cur, payload=str(cur.player.hp))
            self._last_low_hp_emit = cur.timestamp

        # Low/zero ammo
        if cur.player.ammo_in_mag is not None and cur.player.weapon_primary is not None:
            if cur.player.ammo_in_mag == 0:
                bus.emit(GameEvent.OUT_OF_AMMO, cur)
            elif (
                cur.player.ammo_in_mag <= _low_ammo_threshold(cur.player.weapon_primary.kind)
                and cur.timestamp - self._last_low_ammo_emit > 4.0
            ):
                bus.emit(GameEvent.LOW_AMMO, cur, payload=str(cur.player.ammo_in_mag))
                self._last_low_ammo_emit = cur.timestamp

        # Ultimate ready (rising edge)
        if (
            prev.player.ult_pct is not None
            and cur.player.ult_pct is not None
            and prev.player.ult_pct < 1.0
            and cur.player.ult_pct >= 1.0
        ):
            bus.emit(GameEvent.ULTIMATE_READY, cur)

        # Ring closing soon (rising edge)
        if (
            cur.ring.seconds_to_close is not None
            and cur.ring.seconds_to_close <= RING_SOON_SECONDS
            and (
                prev.ring.seconds_to_close is None or prev.ring.seconds_to_close > RING_SOON_SECONDS
            )
        ):
            bus.emit(GameEvent.RING_CLOSING_SOON, cur)

        # Outside ring (rising edge)
        if prev.ring.inside and not cur.ring.inside:
            bus.emit(GameEvent.OUTSIDE_RING, cur)

        # Squad changes
        prev_knocked = {m.slot for m in prev.squad.members if m.knocked}
        cur_knocked = {m.slot for m in cur.squad.members if m.knocked}
        for slot in cur_knocked - prev_knocked:
            bus.emit(GameEvent.TEAMMATE_KNOCKED, cur, payload=str(slot))

        prev_alive = {m.slot for m in prev.squad.members if m.alive}
        cur_alive = {m.slot for m in cur.squad.members if m.alive}
        for slot in prev_alive - cur_alive:
            bus.emit(GameEvent.TEAMMATE_DEATH, cur, payload=str(slot))

        # New legend detections (one event per slot when slug first identified
        # or changes — handy for the AI coach to call set_legend()).
        prev_legends = {m.slot: m.legend_slug for m in prev.squad.members}
        for m in cur.squad.members:
            if m.legend_slug is None:
                continue
            if prev_legends.get(m.slot) != m.legend_slug:
                bus.emit(GameEvent.LEGEND_DETECTED, cur, payload=f"{m.slot}:{m.legend_slug}")

        # Kill feed -> enemy kill / third-party risk
        for ev in kill_events:
            if ev.near_us:
                bus.emit(GameEvent.THIRD_PARTY_RISK, cur, payload=ev.raw)
            else:
                bus.emit(GameEvent.ENEMY_KILLED, cur, payload=ev.raw)


def _median_or_none(window: deque[int]) -> int | None:
    if not window:
        return None
    return int(statistics.median(window))


def _low_ammo_threshold(kind: WeaponType) -> int:
    """Roughly 30% of a typical magazine, broken down by weapon class."""
    return {
        WeaponType.LMG: 12,
        WeaponType.AR: 8,
        WeaponType.SMG: 8,
        WeaponType.MARKSMAN: 4,
        WeaponType.SNIPER: 3,
        WeaponType.SHOTGUN: 2,
        WeaponType.PISTOL: 4,
    }.get(kind, 6)


def _phase_from(prev_phase: MatchPhase, ring: RingState | None) -> MatchPhase:
    """Heuristic match-phase classifier.

    Once we leave UNKNOWN we never go backwards. The classifier uses the
    storm ring countdown — that's the most reliable signal we have without
    reading the in-game clock.
    """
    if ring is None or ring.seconds_to_close is None:
        return prev_phase
    if prev_phase == MatchPhase.UNKNOWN:
        return MatchPhase.EARLY
    if ring.seconds_to_close < 20 and prev_phase.value < MatchPhase.ENDGAME.value:
        return MatchPhase.ENDGAME
    if ring.seconds_to_close < 60 and prev_phase.value < MatchPhase.LATE.value:
        return MatchPhase.LATE
    if ring.seconds_to_close < 120 and prev_phase.value < MatchPhase.MID.value:
        return MatchPhase.MID
    return prev_phase
