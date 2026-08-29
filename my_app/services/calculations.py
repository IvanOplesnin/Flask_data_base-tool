"""Чистая доменная логика расчёта режимов резания."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CuttingParameters:
    cutting_force: float
    cutting_temperature: float
    tool_life: float


def calculate_cutting_parameters(
    force_coefficient: float,
    temperature_coefficient: float,
    durability_coefficient: float,
    cutting_speed: float,
    feed_per_tooth: float,
) -> CuttingParameters:
    """Рассчитывает параметры и не допускает нулевые/отрицательные входы."""
    if cutting_speed <= 0 or feed_per_tooth <= 0:
        raise ValueError('cutting_speed и feed_per_tooth должны быть больше нуля')

    return CuttingParameters(
        cutting_force=force_coefficient * cutting_speed ** -0.12 * feed_per_tooth ** 0.95,
        cutting_temperature=temperature_coefficient * cutting_speed ** 0.4 * feed_per_tooth ** 0.24,
        tool_life=durability_coefficient * cutting_speed ** -0.2 * feed_per_tooth ** -0.15,
    )
