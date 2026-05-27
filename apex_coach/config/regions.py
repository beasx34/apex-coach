"""HUD region presets for common resolutions.

All coordinates are expressed as fractions of the screen via :class:`FractionalRect`
so the same layout scales to any resolution. Each preset is calibrated against the
default Apex Legends HUD as of Season 22+.

If a future patch redesigns the HUD or you play on a non-standard resolution,
adjust the relevant ``FractionalRect`` here or run the (planned) calibration wizard.
"""

from __future__ import annotations

from dataclasses import dataclass

from apex_coach.utils.geometry import FractionalRect


@dataclass(frozen=True, slots=True)
class HudLayout:
    """Fractional positions of every HUD ROI we read.

    These rectangles cover the readable regions only — not the full HUD widget.
    For example, ``hp_value`` is the numeric "100" text, not the bar.
    """

    # Bottom-left player vitals
    hp_value: FractionalRect
    shield_value: FractionalRect
    shield_bar: FractionalRect  # used to detect shield tier by color (white/blue/purple/red)

    # Bottom-right ammo / weapon
    ammo_in_mag: FractionalRect
    ammo_reserve: FractionalRect
    weapon_slot_1: FractionalRect
    weapon_slot_2: FractionalRect

    # Bottom-center / left abilities
    legend_ability: FractionalRect
    ultimate: FractionalRect

    # Squad strip
    squad_panel: FractionalRect

    # Top-left minimap
    minimap: FractionalRect
    ring_timer: FractionalRect

    # Top-right kill feed
    kill_feed: FractionalRect


# Coordinates are tuned against 1920x1080 reference screenshots, then expressed
# as fractions so they apply to any 16:9 resolution. Ultrawide users should
# create a custom preset.
LAYOUT_DEFAULT = HudLayout(
    hp_value=FractionalRect(x=0.030, y=0.905, w=0.040, h=0.030),
    shield_value=FractionalRect(x=0.030, y=0.870, w=0.040, h=0.025),
    shield_bar=FractionalRect(x=0.030, y=0.860, w=0.130, h=0.012),
    ammo_in_mag=FractionalRect(x=0.890, y=0.905, w=0.040, h=0.040),
    ammo_reserve=FractionalRect(x=0.935, y=0.905, w=0.040, h=0.040),
    weapon_slot_1=FractionalRect(x=0.780, y=0.870, w=0.090, h=0.060),
    weapon_slot_2=FractionalRect(x=0.880, y=0.870, w=0.090, h=0.060),
    legend_ability=FractionalRect(x=0.460, y=0.880, w=0.030, h=0.060),
    ultimate=FractionalRect(x=0.510, y=0.880, w=0.030, h=0.060),
    squad_panel=FractionalRect(x=0.005, y=0.150, w=0.130, h=0.130),
    minimap=FractionalRect(x=0.005, y=0.010, w=0.140, h=0.140),
    ring_timer=FractionalRect(x=0.155, y=0.010, w=0.080, h=0.025),
    kill_feed=FractionalRect(x=0.750, y=0.040, w=0.240, h=0.180),
)


PRESETS: dict[str, HudLayout] = {
    # Same fractional rects work for every 16:9 resolution because they scale.
    "1080p": LAYOUT_DEFAULT,
    "1440p": LAYOUT_DEFAULT,
    "4k": LAYOUT_DEFAULT,
}


def get_preset(name: str) -> HudLayout:
    """Look up a preset by name, raising :class:`KeyError` if unknown."""
    try:
        return PRESETS[name.lower()]
    except KeyError as exc:
        raise KeyError(f"Unknown HUD preset {name!r}. Available: {sorted(PRESETS)}") from exc
