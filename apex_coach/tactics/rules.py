"""Deterministic tactical rules.

Bound to :class:`EventBus`. Each handler converts an event into a short Russian
:class:`Tip` pushed to :class:`TipHub`. Rules run in well under 1 ms so they
cover reactive advice without LLM latency.
"""

from __future__ import annotations

from dataclasses import dataclass

from apex_coach.state.events import EventBus
from apex_coach.state.models import (
    GameEvent,
    GameEventInstance,
    GameState,
    MatchPhase,
)
from apex_coach.tactics.knowledge import WEAPON_CLASS_RU, lookup_legend
from apex_coach.utils.logging import get_logger

_log = get_logger("rules")


class TipPriority:
    """Plain integer constants. Using a class instead of IntEnum keeps
    comparisons against raw ints free of cast noise."""

    INFO = 0
    SUGGESTION = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(frozen=True, slots=True)
class Tip:
    """A single piece of advice to show in the overlay."""

    text: str
    priority: int
    source: str  # "rules" | "ai"
    ttl_s: float = 6.0


class TipSink:
    """Anything that accepts :class:`Tip`s. Decouples rules from overlay code."""

    def push(self, tip: Tip) -> None:  # pragma: no cover — interface only
        raise NotImplementedError


class RulesEngine:
    """Subscribes to events and pushes deterministic tips.

    The engine is intentionally stateless beyond the de-bouncing already done by
    :class:`StateAggregator`. Tips are short, Russian, imperative.
    """

    def __init__(self, bus: EventBus, sink: TipSink, current_legend: str | None = None) -> None:
        self._sink = sink
        self._legend_slug = current_legend
        bus.subscribe(GameEvent.LOW_HP, self._on_low_hp)
        bus.subscribe(GameEvent.SHIELD_BROKEN, self._on_shield_broken)
        bus.subscribe(GameEvent.LOW_AMMO, self._on_low_ammo)
        bus.subscribe(GameEvent.OUT_OF_AMMO, self._on_out_of_ammo)
        bus.subscribe(GameEvent.RING_CLOSING_SOON, self._on_ring_closing)
        bus.subscribe(GameEvent.OUTSIDE_RING, self._on_outside_ring)
        bus.subscribe(GameEvent.TEAMMATE_KNOCKED, self._on_teammate_knocked)
        bus.subscribe(GameEvent.THIRD_PARTY_RISK, self._on_third_party)
        bus.subscribe(GameEvent.ULTIMATE_READY, self._on_ult_ready)

    def set_legend(self, slug: str | None) -> None:
        """Tell the engine which legend the local player picked (for ult tips)."""
        self._legend_slug = slug

    # ------------------------------------------------------------------
    # rule handlers
    # ------------------------------------------------------------------
    def _on_low_hp(self, state: GameState, _ev: GameEventInstance) -> None:
        hp = state.player.hp or 0
        text = "Хились! Уходи в укрытие." if hp > 0 else "Замес — лечись срочно!"
        self._sink.push(Tip(text=text, priority=TipPriority.CRITICAL, source="rules", ttl_s=5.0))

    def _on_shield_broken(self, _state: GameState, _ev: GameEventInstance) -> None:
        self._sink.push(
            Tip(
                text="Щит пробит — бат за укрытие или отступай.",
                priority=TipPriority.HIGH,
                source="rules",
            )
        )

    def _on_low_ammo(self, state: GameState, _ev: GameEventInstance) -> None:
        weapon = state.player.weapon_primary
        text = (
            f"Мало патронов в {WEAPON_CLASS_RU[weapon.kind]} — перезаряжай или меняй ствол."
            if weapon is not None
            else "Мало патронов — перезаряжай или меняй ствол."
        )
        self._sink.push(Tip(text=text, priority=TipPriority.HIGH, source="rules", ttl_s=4.0))

    def _on_out_of_ammo(self, _state: GameState, _ev: GameEventInstance) -> None:
        self._sink.push(
            Tip(
                text="Пусто! Достань вторую пушку, не стой.",
                priority=TipPriority.CRITICAL,
                source="rules",
                ttl_s=4.0,
            )
        )

    def _on_ring_closing(self, state: GameState, _ev: GameEventInstance) -> None:
        direction = state.ring.direction_to_center or state.minimap.ring_direction
        if direction:
            text = f"Кольцо схлопывается — ротация на {direction}."
        else:
            text = "Кольцо схлопывается — готовь ротацию в круг."
        self._sink.push(Tip(text=text, priority=TipPriority.HIGH, source="rules", ttl_s=8.0))

    def _on_outside_ring(self, _state: GameState, _ev: GameEventInstance) -> None:
        self._sink.push(
            Tip(
                text="Ты вне круга — беги в круг, не задерживайся в бою.",
                priority=TipPriority.CRITICAL,
                source="rules",
            )
        )

    def _on_teammate_knocked(self, state: GameState, _ev: GameEventInstance) -> None:
        if state.match_phase == MatchPhase.ENDGAME:
            text = "Тиммейт упал. В финале — добей врага, потом поднимай."
        else:
            text = "Тиммейт упал — прикрой и поднимай, дави дымом/щитом."
        self._sink.push(Tip(text=text, priority=TipPriority.CRITICAL, source="rules", ttl_s=8.0))

    def _on_third_party(self, _state: GameState, _ev: GameEventInstance) -> None:
        self._sink.push(
            Tip(
                text="Рядом кил — добивай быстро или отходи, едет тёрд-парти.",
                priority=TipPriority.HIGH,
                source="rules",
                ttl_s=6.0,
            )
        )

    def _on_ult_ready(self, _state: GameState, _ev: GameEventInstance) -> None:
        if self._legend_slug:
            info = lookup_legend(self._legend_slug)
            if info is not None:
                self._sink.push(
                    Tip(
                        text=info.tactical_ult_tip_ru,
                        priority=TipPriority.SUGGESTION,
                        source="rules",
                    )
                )
                return
        self._sink.push(
            Tip(
                text="Ульта готова — используй вовремя, не сидим на ней.",
                priority=TipPriority.SUGGESTION,
                source="rules",
            )
        )
