"""TipHub queue / dedup / priority tests."""

from __future__ import annotations

from apex_coach.overlay.tip_hub import TipHub
from apex_coach.tactics.rules import Tip, TipPriority


def test_dedup_within_window() -> None:
    hub = TipHub()
    received: list[Tip | None] = []
    hub.set_listener(received.append)
    tip = Tip(text="Hello", priority=TipPriority.HIGH, source="rules", ttl_s=10.0)
    hub.push(tip)
    hub.push(tip)
    assert len(received) == 1


def test_higher_priority_replaces_lower() -> None:
    hub = TipHub()
    received: list[Tip | None] = []
    hub.set_listener(received.append)
    hub.push(Tip(text="Suggest", priority=TipPriority.SUGGESTION, source="rules"))
    hub.push(Tip(text="Critical", priority=TipPriority.CRITICAL, source="rules"))
    assert received[-1] is not None
    assert received[-1].text == "Critical"


def test_lower_priority_is_suppressed_while_higher_active() -> None:
    hub = TipHub()
    received: list[Tip | None] = []
    hub.set_listener(received.append)
    hub.push(Tip(text="Critical", priority=TipPriority.CRITICAL, source="rules", ttl_s=10.0))
    hub.push(Tip(text="Info", priority=TipPriority.INFO, source="rules"))
    assert len(received) == 1
    assert received[0] is not None
    assert received[0].text == "Critical"
