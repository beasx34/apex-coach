"""Tiny in-process pub/sub bus for game events."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from apex_coach.state.models import GameEvent, GameEventInstance, GameState
from apex_coach.utils.logging import get_logger

_log = get_logger("events")

EventHandler = Callable[[GameState, GameEventInstance], None]


class EventBus:
    """Synchronous, single-threaded event bus.

    Handlers run inline on the emitter thread — they MUST be fast and non-blocking.
    Heavy work (e.g. LLM calls) should be dispatched to an asyncio task.
    """

    def __init__(self) -> None:
        self._subs: dict[GameEvent, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event: GameEvent, handler: EventHandler) -> None:
        self._subs[event].append(handler)

    def emit(self, event: GameEvent, state: GameState, payload: str | None = None) -> None:
        instance = GameEventInstance(event=event, timestamp=state.timestamp, payload=payload)
        state.recent_events.append(instance)
        for handler in self._subs.get(event, ()):
            try:
                handler(state, instance)
            except Exception:  # pragma: no cover — defensive
                _log.exception("Event handler for %s failed", event)


__all__ = ["EventBus", "EventHandler"]
