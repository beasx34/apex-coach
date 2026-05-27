"""High-level AI coach: decides when to ask Gemini and pushes the answer to TipHub."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from apex_coach.ai.prompts import SYSTEM_PROMPT_RU, build_user_prompt
from apex_coach.state.events import EventBus
from apex_coach.state.models import GameEvent, GameEventInstance, GameState
from apex_coach.tactics.rules import Tip, TipPriority, TipSink
from apex_coach.utils.logging import get_logger

if TYPE_CHECKING:
    from apex_coach.ai.gemini import GeminiClient

_log = get_logger("ai-coach")


# Events that justify burning a Gemini call. Mundane "took some damage" doesn't.
_TRIGGER_EVENTS = frozenset(
    {
        GameEvent.RING_CLOSING_SOON,
        GameEvent.TEAMMATE_KNOCKED,
        GameEvent.OUTSIDE_RING,
        GameEvent.THIRD_PARTY_RISK,
        GameEvent.ENEMY_KILLED,
        GameEvent.ULTIMATE_READY,
    }
)


class AiCoach:
    """Rate-limited, event-driven Gemini coach.

    Responsibilities:
      * Decide when to call the LLM (debounce + cooldown).
      * Build the prompt from the current :class:`GameState`.
      * Push the answer to :class:`TipSink` when it arrives.

    A single :func:`asyncio.Task` is kept in flight at a time — if a new
    trigger fires while we're still waiting, it's coalesced.
    """

    def __init__(
        self,
        client: GeminiClient,
        bus: EventBus,
        sink: TipSink,
        meta_notes: str,
        *,
        min_interval_s: float = 8.0,
    ) -> None:
        self._client = client
        self._sink = sink
        self._system_prompt = SYSTEM_PROMPT_RU.format(meta_notes=meta_notes)
        self._min_interval_s = min_interval_s
        self._last_request_at = 0.0
        self._in_flight: asyncio.Task[None] | None = None
        self._legend: str | None = None
        self._latest_state: GameState | None = None
        for ev in _TRIGGER_EVENTS:
            bus.subscribe(ev, self._on_event)

    def set_legend(self, slug: str | None) -> None:
        self._legend = slug

    def update_state(self, state: GameState) -> None:
        """Keep the latest snapshot — hotkey-triggered requests need this."""
        self._latest_state = state

    # ------------------------------------------------------------------
    # event handler / manual trigger
    # ------------------------------------------------------------------
    def _on_event(self, state: GameState, _ev: GameEventInstance) -> None:
        self._latest_state = state
        self._maybe_request(state)

    def request_now(self) -> None:
        """Bypass rate limit (within reason) when the user pressed the hotkey."""
        if self._latest_state is None:
            return
        # Allow manual requests sooner — but still respect a 2-second minimum
        # to protect against accidental key spam.
        if time.monotonic() - self._last_request_at < 2.0:
            return
        self._dispatch(self._latest_state)

    def _maybe_request(self, state: GameState) -> None:
        now = time.monotonic()
        if now - self._last_request_at < self._min_interval_s:
            return
        if self._in_flight is not None and not self._in_flight.done():
            return
        self._dispatch(state)

    def _dispatch(self, state: GameState) -> None:
        self._last_request_at = time.monotonic()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _log.debug("AiCoach._dispatch called with no running loop; skipping.")
            return
        self._in_flight = loop.create_task(self._run(state))

    async def _run(self, state: GameState) -> None:
        prompt = build_user_prompt(state, self._legend)
        try:
            answer = await self._client.generate(self._system_prompt, prompt)
        except Exception:
            _log.warning("Gemini call failed — falling back to rules only", exc_info=True)
            return
        if not answer:
            return
        self._sink.push(
            Tip(
                text=answer,
                priority=TipPriority.SUGGESTION,
                source="ai",
                ttl_s=10.0,
            )
        )


__all__ = ["AiCoach"]
