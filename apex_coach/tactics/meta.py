"""Loads sliding meta notes from a markdown file shipped under ``resources/``.

The whole file is embedded in the Gemini system prompt — keep it short
(under ~400 tokens) for latency.
"""

from __future__ import annotations

from pathlib import Path

_DEFAULT_META = """\
Сезон: общий (без актуальной меты — обнови resources/meta_ru.md).
Сильные стволы по умолчанию: R-301, Volt, Flatline.
Помни про ребаланс брони — белый щит = 50, синий = 75, фиолет = 100, красный = 125.
"""


def load_meta_notes(resources_dir: Path) -> str:
    """Return meta-notes text. Falls back to a generic stub if the file is missing."""
    candidate = resources_dir / "meta_ru.md"
    if candidate.is_file():
        try:
            return candidate.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return _DEFAULT_META.strip()
