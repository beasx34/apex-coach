"""Prompt templates for the Gemini coach. Russian-only for the MVP."""

from __future__ import annotations

from apex_coach.state.models import GameState, ShieldTier
from apex_coach.tactics.knowledge import WEAPON_CLASS_RU

SYSTEM_PROMPT_RU = """\
Ты — тренер-командирор по Apex Legends, говоришь по-русски и кратко.
Твой формат ответа: ОДИН тактический совет на ближайшие 10-20 секунд игры.
Максимум 2 коротких предложения. Без приветствий, без оговорок, без эмодзи,
без объяснений почему. Только команда игроку.

Учитывай актуальную мету сезона:
{meta_notes}

Если данных мало или ситуация спокойная — скажи коротко, что делать сейчас
(лут, ротация, позиционирование), не больше одного предложения.
"""


_USER_PROMPT_TEMPLATE_RU = """\
Состояние игрока:
- Легенда: {legend}
- HP {hp}/100, Щит {shield}/{shield_max} ({shield_tier})
- Оружие 1: {weapon_primary} (патроны {ammo_mag}/{ammo_reserve})
- Оружие 2: {weapon_secondary}
- Способность: {ability_state}, Ульта: {ult_state}

Команда:
- Живых: {squad_alive}/3, кто-то в нокдауне: {squad_knocked}

Кольцо:
- Фаза: {match_phase}
- До схлопывания: {ring_time}
- Направление центра: {ring_direction}
- В круге: {in_ring}

Последние события (последние 10 сек):
{recent_events}

Дай ОДИН совет на ближайшие 10-20 сек. Только команда, без воды.
"""


def build_user_prompt(state: GameState, legend: str | None) -> str:
    """Render the user-turn prompt from the current :class:`GameState`."""
    p = state.player
    tier = p.shield_tier
    shield_tier_ru = {
        ShieldTier.NONE: "нет",
        ShieldTier.WHITE: "белый",
        ShieldTier.BLUE: "синий",
        ShieldTier.PURPLE: "фиолет",
        ShieldTier.RED: "красный",
    }[tier]
    weapon_primary = (
        f"{p.weapon_primary.name} ({WEAPON_CLASS_RU[p.weapon_primary.kind]})"
        if p.weapon_primary is not None
        else "нет"
    )
    weapon_secondary = (
        f"{p.weapon_secondary.name} ({WEAPON_CLASS_RU[p.weapon_secondary.kind]})"
        if p.weapon_secondary is not None
        else "нет"
    )
    if p.ability_cd_s is None or p.ability_cd_s <= 0:
        ability_state = "готова"
    else:
        ability_state = f"кд {int(p.ability_cd_s)}с"
    ult_state = (
        "готова"
        if p.ult_pct is not None and p.ult_pct >= 1.0
        else (f"{int((p.ult_pct or 0) * 100)}%")
    )
    recent = "\n".join(f"- {e.event.name} ({e.payload or '-'})" for e in state.recent_events) or "—"
    ring_time = (
        f"{int(state.ring.seconds_to_close)}с"
        if state.ring.seconds_to_close is not None
        else "неизвестно"
    )
    return _USER_PROMPT_TEMPLATE_RU.format(
        legend=legend or "не выбрана",
        hp=p.hp if p.hp is not None else "?",
        shield=p.shield if p.shield is not None else "?",
        shield_max=tier.max_shield or "?",
        shield_tier=shield_tier_ru,
        weapon_primary=weapon_primary,
        weapon_secondary=weapon_secondary,
        ammo_mag=p.ammo_in_mag if p.ammo_in_mag is not None else "?",
        ammo_reserve=p.ammo_reserve if p.ammo_reserve is not None else "?",
        ability_state=ability_state,
        ult_state=ult_state,
        squad_alive=state.squad.alive_count,
        squad_knocked="да" if state.squad.anyone_knocked else "нет",
        match_phase=state.match_phase.name.lower(),
        ring_time=ring_time,
        ring_direction=state.ring.direction_to_center
        or state.minimap.ring_direction
        or "неизвестно",
        in_ring="да" if state.ring.inside else "нет",
        recent_events=recent,
    )
