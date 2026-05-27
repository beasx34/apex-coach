"""Thin async wrapper over ``google-genai``.

Why a wrapper rather than calling the SDK directly?

- We want a tiny, mockable interface in tests.
- We need a single place to swap between streaming and non-streaming.
- We may eventually retry on transient errors; one client is the right home.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from apex_coach.utils.logging import get_logger

_log = get_logger("gemini")


class GeminiClient:
    """Calls Gemini 2.5 Flash on the Google AI Studio free tier.

    The client is constructed lazily on first call to avoid paying SDK import
    cost (or hitting auth errors) at startup when the user has no key.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")
        self._api_key = api_key
        self._model = model
        self._client: object | None = None

    def _ensure_client(self) -> object:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def generate(self, system: str, user: str, *, timeout_s: float = 12.0) -> str:
        """Single-shot non-streaming generation.

        Runs the synchronous SDK call on the default executor with a timeout so
        a stuck request never blocks the main loop.
        """

        def _call() -> str:
            client = self._ensure_client()
            response = client.models.generate_content(  # type: ignore[attr-defined]
                model=self._model,
                contents=user,
                config={"system_instruction": system, "temperature": 0.4, "max_output_tokens": 120},
            )
            return (response.text or "").strip()

        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(loop.run_in_executor(None, _call), timeout=timeout_s)

    async def stream(
        self, system: str, user: str, *, timeout_s: float = 12.0
    ) -> AsyncIterator[str]:
        """Streaming generation: yields incremental text chunks.

        Implemented on top of :meth:`generate` for simplicity — we already cap
        tokens at ~120 so the latency win from streaming is marginal. Keeping
        the API in case we want true streaming later.
        """
        text = await self.generate(system, user, timeout_s=timeout_s)
        yield text
