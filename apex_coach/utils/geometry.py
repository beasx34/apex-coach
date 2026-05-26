"""Geometry primitives shared across capture / vision / config."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rect:
    """Axis-aligned rectangle in absolute pixels."""

    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    def as_mss_dict(self) -> dict[str, int]:
        """Return the rect in the format mss.grab() expects."""
        return {"left": self.x, "top": self.y, "width": self.w, "height": self.h}


@dataclass(frozen=True, slots=True)
class FractionalRect:
    """Rectangle in [0, 1] fractions of the screen.

    Keeps HUD region definitions resolution-independent.
    """

    x: float
    y: float
    w: float
    h: float

    def to_pixels(self, screen_w: int, screen_h: int) -> Rect:
        return Rect(
            x=int(round(self.x * screen_w)),
            y=int(round(self.y * screen_h)),
            w=int(round(self.w * screen_w)),
            h=int(round(self.h * screen_h)),
        )
