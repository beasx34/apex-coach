"""Static knowledge tables.

Hand-curated content that changes once per Apex patch. Keeping it in code
(rather than YAML) means refactors flow through type checking.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from apex_coach.state.models import WeaponType


class LegendRole(Enum):
    ASSAULT = "Штурмовик"
    SKIRMISHER = "Бегун"
    RECON = "Разведчик"
    SUPPORT = "Поддержка"
    CONTROLLER = "Контролёр"


@dataclass(frozen=True, slots=True)
class LegendInfo:
    """Compact data about a single legend."""

    name: str  # Russian display name
    role: LegendRole
    tactical_ult_tip_ru: str  # short tip shown when ult comes off cooldown


# Update on every season/patch that ships a new legend or reworks an existing one.
LEGEND_KB: dict[str, LegendInfo] = {
    "gibraltar": LegendInfo(
        name="Гибралтар",
        role=LegendRole.SUPPORT,
        tactical_ult_tip_ru="Ульта готова — кидай арт-удар для пуша или зачистки укрытия.",
    ),
    "bangalore": LegendInfo(
        name="Бангалор",
        role=LegendRole.ASSAULT,
        tactical_ult_tip_ru="Ульта готова — оставь её для отхода/слома пуша противника.",
    ),
    "wraith": LegendInfo(
        name="Рэйф",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — портал для ротации или эвакуации с боя.",
    ),
    "pathfinder": LegendInfo(
        name="Патфайндер",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — зиплайн для высокой точки или быстрой ротации.",
    ),
    "bloodhound": LegendInfo(
        name="Бладхаунд",
        role=LegendRole.RECON,
        tactical_ult_tip_ru="Ульта готова — пуш с подсветкой врагов после первого замеса.",
    ),
    "lifeline": LegendInfo(
        name="Лайфлайн",
        role=LegendRole.SUPPORT,
        tactical_ult_tip_ru="Ульта готова — сейф под прикрытием стенки для разбора луталки.",
    ),
    "caustic": LegendInfo(
        name="Каустик",
        role=LegendRole.CONTROLLER,
        tactical_ult_tip_ru="Ульта готова — газ в чокпойнт перед круг-сжатием.",
    ),
    "mirage": LegendInfo(
        name="Мираж",
        role=LegendRole.SUPPORT,
        tactical_ult_tip_ru="Ульта готова — клон-стая для отвлечения и поднятия союзника.",
    ),
    "octane": LegendInfo(
        name="Октан",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — батут для высокого ангажмента или скоростного отхода.",
    ),
    "wattson": LegendInfo(
        name="Уоттсон",
        role=LegendRole.CONTROLLER,
        tactical_ult_tip_ru="Ульта готова — поставь Пилон под щитки и финал круга.",
    ),
    "crypto": LegendInfo(
        name="Крипто",
        role=LegendRole.RECON,
        tactical_ult_tip_ru="Ульта готова — EMP-дрон выбьет щиты и сорвёт укрытия перед пушем.",
    ),
    "revenant": LegendInfo(
        name="Ревенант",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — теневая защита для безнаказанного пуша на оборону.",
    ),
    "loba": LegendInfo(
        name="Лоба",
        role=LegendRole.SUPPORT,
        tactical_ult_tip_ru="Ульта готова — Чёрный рынок для добора щитов/патронов всей командой.",
    ),
    "rampart": LegendInfo(
        name="Рэмпарт",
        role=LegendRole.CONTROLLER,
        tactical_ult_tip_ru="Ульта готова — Шейла под пуш или для удержания чокпойнта в финале.",
    ),
    "horizon": LegendInfo(
        name="Хорайзон",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — чёрная дыра для финиша группы в укрытии.",
    ),
    "fuse": LegendInfo(
        name="Фьюз",
        role=LegendRole.ASSAULT,
        tactical_ult_tip_ru="Ульта готова — кольцо огня для зонирования и сжатия противника.",
    ),
    "valkyrie": LegendInfo(
        name="Валькирия",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — реактивный взлёт для ранней ротации в финал.",
    ),
    "seer": LegendInfo(
        name="Сиир",
        role=LegendRole.RECON,
        tactical_ult_tip_ru="Ульта готова — поставь под подозрительное здание перед пушем.",
    ),
    "ash": LegendInfo(
        name="Эш",
        role=LegendRole.ASSAULT,
        tactical_ult_tip_ru="Ульта готова — открой портал в сторону отходящего противника.",
    ),
    "maggie": LegendInfo(
        name="Мэгги",
        role=LegendRole.ASSAULT,
        tactical_ult_tip_ru="Ульта готова — шары с ускорением через коридор атаки.",
    ),
    "vantage": LegendInfo(
        name="Вантедж",
        role=LegendRole.RECON,
        tactical_ult_tip_ru="Ульта готова — стакай маркер на одну цель перед командной атакой.",
    ),
    "newcastle": LegendInfo(
        name="Ньюкасл",
        role=LegendRole.SUPPORT,
        tactical_ult_tip_ru="Ульта готова — крепость для тех-боя на узком чокпойнте.",
    ),
    "catalyst": LegendInfo(
        name="Каталист",
        role=LegendRole.CONTROLLER,
        tactical_ult_tip_ru="Ульта готова — стена для зонирования финального круга.",
    ),
    "ballistic": LegendInfo(
        name="Баллистик",
        role=LegendRole.ASSAULT,
        tactical_ult_tip_ru="Ульта готова — буст для агрессивного пуша или клатча.",
    ),
    "conduit": LegendInfo(
        name="Кондуит",
        role=LegendRole.SUPPORT,
        tactical_ult_tip_ru="Ульта готова — джаммеры для удержания позиции/слома пуша.",
    ),
    "alter": LegendInfo(
        name="Альтер",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — портал на эвакуацию команды после неудачного боя.",
    ),
    "sparrow": LegendInfo(
        name="Спэрроу",
        role=LegendRole.SKIRMISHER,
        tactical_ult_tip_ru="Ульта готова — лук с разрывными для бурст-урона по группе.",
    ),
}


def lookup_legend(slug: str) -> LegendInfo | None:
    return LEGEND_KB.get(slug.lower())


# Display labels for weapon classes in Russian tips.
WEAPON_CLASS_RU: dict[WeaponType, str] = {
    WeaponType.AR: "штурмовая винтовка",
    WeaponType.SMG: "ПП",
    WeaponType.LMG: "пулемёт",
    WeaponType.SNIPER: "снайперка",
    WeaponType.MARKSMAN: "марксман",
    WeaponType.SHOTGUN: "дробовик",
    WeaponType.PISTOL: "пистолет",
    WeaponType.UNKNOWN: "оружие",
}
