"""Подбор исходных данных расчёта из справочников проекта."""

from __future__ import annotations

from dataclasses import dataclass

from my_app.extensions import db
from my_app.models import Coating, Coefficient, Material, RecommendationParameter, Tool


@dataclass(frozen=True)
class CuttingReference:
    """Нормализованный набор параметров для калькулятора."""

    material_id: int
    tool_id: int
    coating_id: int
    material_name: str
    tool_name: str
    coating_name: str
    kc1: float | None = None
    mc: float | None = None
    base_cutting_speed: float | None = None
    base_feed_per_tooth: float | None = None
    base_feed_per_revolution: float | None = None
    rake_angle: float | None = None
    source: str = 'none'

    def as_dict(self) -> dict:
        result = {
            'material_id': self.material_id,
            'tool_id': self.tool_id,
            'coating_id': self.coating_id,
            'material_name': self.material_name,
            'tool_name': self.tool_name,
            'coating_name': self.coating_name,
            'source': self.source,
        }
        for field_name in (
            'kc1', 'mc', 'base_cutting_speed', 'base_feed_per_tooth',
            'base_feed_per_revolution', 'rake_angle',
        ):
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        return result


def _positive_or_none(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _first_rake_angle(tool: Tool) -> float | None:
    for insert in tool.insert or ():
        if insert.rake_angle is not None:
            return float(insert.rake_angle)
    return None


def _recommendation_value(recommendation, attribute: str):
    try:
        return getattr(recommendation, attribute)
    except (AttributeError, TypeError, ZeroDivisionError):
        return None


def get_cutting_reference(material_id, tool_id, coating_id) -> CuttingReference | None:
    """Возвращает коэффициенты для выбранной тройки справочников.

    Базовые скорость и подача берутся из ``Coefficient``. Если их там ещё
    нет, используются существующие ``RecommendationParameter`` для фрезы.
    Исторические поля ``cutting_force_coefficient`` намеренно не маппятся в
    ``kc1``: у них другая размерность и другая эмпирическая модель.
    """

    try:
        material_id = int(material_id)
        tool_id = int(tool_id)
        coating_id = int(coating_id)
    except (TypeError, ValueError):
        return None

    material = db.session.get(Material, material_id)
    tool = db.session.get(Tool, tool_id)
    if material is None or tool is None:
        return None
    coating = db.session.get(Coating, coating_id)
    if coating is None:
        return None

    coefficient = db.session.scalar(db.select(Coefficient).where(
        Coefficient.material_id == material_id,
        Coefficient.tool_id == tool_id,
        Coefficient.coating_id == coating_id,
    ))
    recommendation = db.session.scalar(db.select(RecommendationParameter).where(
        RecommendationParameter.material_id == material_id,
        RecommendationParameter.tool_id == tool_id,
        RecommendationParameter.coating_id == coating_id,
    ))

    base_speed = _positive_or_none(coefficient.base_cutting_speed if coefficient else None)
    base_fz = _positive_or_none(coefficient.base_feed_per_tooth if coefficient else None)
    if recommendation and tool.milling_geometry:
        if base_speed is None:
            base_speed = _positive_or_none(_recommendation_value(recommendation, 'cutter_speed'))
        if base_fz is None:
            base_fz = _positive_or_none(_recommendation_value(recommendation, 'feed_of_teeth'))

    if coefficient:
        source = 'coefficient'
        if recommendation and (base_speed is not None or base_fz is not None):
            source = 'coefficient+recommendation'
    elif recommendation:
        source = 'recommendation'
    else:
        source = 'tool'

    return CuttingReference(
        material_id=material.id,
        tool_id=tool.id,
        coating_id=coating.id,
        material_name=material.name,
        tool_name=tool.name,
        coating_name=coating.name,
        kc1=_positive_or_none(coefficient.kc1 if coefficient else None),
        mc=_positive_or_none(coefficient.mc if coefficient else None),
        base_cutting_speed=base_speed,
        base_feed_per_tooth=base_fz,
        base_feed_per_revolution=_positive_or_none(
            coefficient.base_feed_per_revolution if coefficient else None
        ),
        rake_angle=_first_rake_angle(tool),
        source=source,
    )
