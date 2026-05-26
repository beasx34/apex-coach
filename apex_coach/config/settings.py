"""User configuration. Reads ``config.toml`` from the standard user config dir
plus environment overrides (``GEMINI_API_KEY`` etc.).
"""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class CaptureSettings(BaseModel):
    monitor: int = 1
    target_fps: float = Field(10.0, gt=0, le=60)


class LayoutSettings(BaseModel):
    preset: Literal["1080p", "1440p", "4k"] = "1080p"


class AiSettings(BaseModel):
    model: str = "gemini-2.5-flash"
    min_interval_s: float = Field(8.0, gt=0)
    language: Literal["ru", "en"] = "ru"
    api_key_env: str = "GEMINI_API_KEY"


class OverlaySettings(BaseModel):
    opacity: float = Field(0.85, ge=0.1, le=1.0)
    position: Literal["bottom-left", "bottom-right", "top-left", "top-right"] = "bottom-left"
    tip_ttl_s: float = Field(6.0, gt=0)


class HotkeySettings(BaseModel):
    ai_request: str = "<alt>+`"
    toggle: str = "<alt>+\\"
    calibrate: str = "<alt>+<shift>+c"


class Settings(BaseModel):
    capture: CaptureSettings = CaptureSettings()
    layout: LayoutSettings = LayoutSettings()
    ai: AiSettings = AiSettings()
    overlay: OverlaySettings = OverlaySettings()
    hotkeys: HotkeySettings = HotkeySettings()

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        """Load settings from a TOML file, falling back to defaults if missing."""
        config_path = path or default_config_path()
        if config_path.is_file():
            with config_path.open("rb") as fh:
                raw = tomllib.load(fh)
            return cls.model_validate(raw)
        return cls()

    def resolve_api_key(self) -> str | None:
        """Read the Gemini API key from the configured environment variable."""
        return os.environ.get(self.ai.api_key_env)


def default_config_path() -> Path:
    """Return the standard per-user config path for the current OS."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / "apex-coach" / "config.toml"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "apex-coach" / "config.toml"
