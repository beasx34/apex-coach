"""Domain models for the game state pipeline."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto


class ShieldTier(Enum):
    """Armor tier inferred from the shield bar color."""

    NONE = auto()
    WHITE = auto()
    BLUE = auto()
    PURPLE = auto()
    RED = auto()

    @property
    def max_shield(self) -> int:
        return {
            ShieldTier.NONE: 0,
            ShieldTier.WHITE: 50,
            ShieldTier.BLUE: 75,
            ShieldTier.PURPLE: 100,
            ShieldTier.RED: 125,
        }[self]


class MatchPhase(Enum):
    """Coarse classification of where we are in a match."""

    UNKNOWN = auto()
    DROPPING = auto()
    EARLY = auto()
    MID = auto()
    LATE = auto()
    ENDGAME = auto()


class WeaponType(Enum):
    """High-level weapon class. Used by knowledge base for tactical hints."""

    UNKNOWN = auto()
    AR = auto()
    SMG = auto()
    LMG = auto()
    SNIPER = auto()
    MARKSMAN = auto()
    SHOTGUN = auto()
    PISTOL = auto()


@dataclass(frozen=True, slots=True)
class Weapon:
    """A weapon the player is currently holding."""

    name: str
    kind: WeaponType


@dataclass(slots=True)
class PlayerHud:
    """Single-frame snapshot of the local player's HUD."""

    hp: int | None = None
    shield: int | None = None
    shield_tier: ShieldTier = ShieldTier.NONE
    ammo_in_mag: int | None = None
    ammo_reserve: int | None = None
    weapon_primary: Weapon | None = None
    weapon_secondary: Weapon | None = None
    ability_cd_s: float | None = None  # seconds remaining; 0 means ready
    ult_pct: float | None = None  # 0..1; 1 means ready
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class SquadMember:
    """State of one teammate as inferred from the squad strip."""

    slot: int  # 0..2 (0 is the local player)
    alive: bool
    knocked: bool
    legend_slug: str | None = None  # matches a key in LEGEND_KB; None until detected


@dataclass(slots=True)
class SquadState:
    """Whole-squad state."""

    members: tuple[SquadMember, ...] = ()

    @property
    def anyone_knocked(self) -> bool:
        return any(m.knocked for m in self.members)

    @property
    def alive_count(self) -> int:
        return sum(1 for m in self.members if m.alive and not m.knocked)


@dataclass(slots=True)
class RingState:
    """Information about the storm ring."""

    seconds_to_close: float | None = None
    closing: bool = False
    # Direction from player to ring center as a compass label (e.g. "NW").
    direction_to_center: str | None = None
    inside: bool = True


@dataclass(slots=True)
class KillFeedEvent:
    """One row of the kill feed."""

    raw: str
    killer: str | None
    victim: str | None
    weapon: str | None
    knockdown_only: bool
    near_us: bool  # heuristic — feed has special marker for nearby fights
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(slots=True)
class MinimapSnapshot:
    """Compact view of minimap-derived state."""

    ring_direction: str | None = None  # rough compass label
    visible_enemy_pings: int = 0


@dataclass(slots=True)
class GameState:
    """Aggregated, smoothed state used by both rules and AI coach."""

    player: PlayerHud = field(default_factory=PlayerHud)
    squad: SquadState = field(default_factory=SquadState)
    ring: RingState = field(default_factory=RingState)
    minimap: MinimapSnapshot = field(default_factory=MinimapSnapshot)
    recent_events: deque[GameEventInstance] = field(default_factory=lambda: deque(maxlen=20))
    match_phase: MatchPhase = MatchPhase.UNKNOWN
    timestamp: float = field(default_factory=time.monotonic)


class GameEvent(Enum):
    """Discrete events derived from state diffs."""

    TOOK_DAMAGE = auto()
    SHIELD_BROKEN = auto()
    LOW_HP = auto()
    LOW_AMMO = auto()
    OUT_OF_AMMO = auto()
    TEAMMATE_KNOCKED = auto()
    TEAMMATE_DEATH = auto()
    ENEMY_KILLED = auto()
    RING_CLOSING_SOON = auto()
    OUTSIDE_RING = auto()
    ULTIMATE_READY = auto()
    THIRD_PARTY_RISK = auto()
    LEGEND_DETECTED = (
        auto()
    )  # payload: "slot:slug" (e.g. "0:wraith"); fires once per slot when legend first identified


@dataclass(frozen=True, slots=True)
class GameEventInstance:
    """An emitted event with optional payload and timestamp."""

    event: GameEvent
    timestamp: float
    payload: str | None = None
