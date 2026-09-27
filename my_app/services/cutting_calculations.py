"""Формулы режимов резания по референсным калькуляторам INNER.

Числовые коэффициенты (``kc1``, ``mc`` и коэффициенты скорости) передаются
в функцию из справочника/карточки инструмента. Сами функции не утверждают
универсальные режимы: они проверяют единицы, рассчитывают производные
величины и возвращают предупреждения для технолога.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field


class CalculationInputError(ValueError):
    """Входные данные расчёта не прошли проверку."""


@dataclass(frozen=True)
class CalculationResult:
    processing_type: str
    spindle_speed: float
    feed_rate: float
    cutting_speed: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
    extra: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        result = asdict(self)
        result['warnings'] = list(self.warnings)
        return result


def _positive(value: object, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CalculationInputError(f'{name} должно быть числом больше нуля') from exc
    if not math.isfinite(number) or number <= 0:
        raise CalculationInputError(f'{name} должно быть числом больше нуля')
    return number


def _optional_positive(value: object, name: str) -> float | None:
    if value in (None, ''):
        return None
    return _positive(value, name)


def _factor(value: object, name: str, default: float = 1.0) -> float:
    if value in (None, ''):
        return default
    return _positive(value, name)


def _coolant_warnings(coolant: str | None, material: str | None) -> tuple[str, ...]:
    material_text = (material or '').lower()
    coolant_text = (coolant or '').lower()
    if ('титан' in material_text or 'titan' in material_text) and coolant_text in {'', 'none', 'сухая'}:
        return ('Для титановых сплавов требуется подтвердить применение СОЖ.',)
    return ()


def _coolant_speed_factor(coolant: str | None) -> float:
    """Поправка скорости для режима охлаждения из референсного калькулятора."""

    coolant_text = (coolant or '').lower()
    if coolant_text in {'mql', 'oil', 'масло'}:
        return 0.90
    if coolant_text in {'air', 'обдув'}:
        return 0.85
    if coolant_text in {'none', 'сухая', 'dry'}:
        return 0.80
    return 1.0


def _machine_warnings(
    *,
    spindle_speed: float,
    max_rpm: object | None,
    power_kw: float | None,
    calculated_power_kw: float | None,
) -> list[str]:
    warnings: list[str] = []
    max_rpm_value = _optional_positive(max_rpm, 'Максимальные обороты')
    if max_rpm_value is not None and spindle_speed > max_rpm_value:
        warnings.append(f'Расчётные обороты превышают ограничение станка ({max_rpm_value:g} об/мин).')
    if power_kw is not None and calculated_power_kw is not None and calculated_power_kw > power_kw:
        warnings.append(f'Расчётная мощность {calculated_power_kw:.2f} кВт превышает мощность станка {power_kw:.2f} кВт.')
    return warnings


def _kienzle(
    *,
    kc1: object | None,
    mc: object | None,
    chip_thickness: object | None,
    rake_angle: object | None,
) -> tuple[float, float] | None:
    """Возвращает (удельная сила kc, толщина стружки hm), если есть данные."""

    if kc1 in (None, '') and mc in (None, ''):
        return None
    if kc1 in (None, '') or mc in (None, ''):
        raise CalculationInputError('Для модели Kienzle нужны оба коэффициента kc1 и mc')
    hm = _positive(chip_thickness, 'Толщина среза hm')
    kc1_value = _positive(kc1, 'Коэффициент kc1')
    mc_value = _positive(mc, 'Показатель mc')
    gamma = float(rake_angle or 0)
    kc = kc1_value * hm ** (-mc_value) * (1 - gamma / 100)
    if kc <= 0:
        raise CalculationInputError('Передний угол дал неположительную удельную силу резания')
    return kc, hm


def calculate_milling(
    *,
    cutting_speed: object,
    diameter: object,
    number_teeth: object,
    feed_per_tooth: object | None = None,
    base_feed_per_tooth: object | None = None,
    operation_factor: object | None = None,
    depth_cut: object | None = None,
    width_cut: object | None = None,
    coolant: str | None = None,
    material: str | None = None,
    coolant_factor: object | None = None,
    kc1: object | None = None,
    mc: object | None = None,
    chip_thickness: object | None = None,
    rake_angle: object | None = None,
    max_rpm: object | None = None,
    machine_power: object | None = None,
) -> CalculationResult:
    """Расчёт фрезерования по формулам n, fz, F, RCTF, Q, Pc и Mc.

    Если задана базовая подача ``fz(base)``, применяется масштабирование
    ``fz = fz(base) * sqrt(D / 10) * Kоперации``.
    Для Kienzle предпочтительно передавать фактическую среднюю толщину
    стружки ``hm``; если она не задана, используется ``fz`` как приближение.
    """

    speed = _positive(cutting_speed, 'Скорость резания')
    speed *= _factor(coolant_factor, 'Коэффициент СОЖ', default=_coolant_speed_factor(coolant))
    diameter_value = _positive(diameter, 'Диаметр фрезы')
    teeth = _positive(number_teeth, 'Количество зубьев')
    if feed_per_tooth not in (None, ''):
        feed_tooth = _positive(feed_per_tooth, 'Подача на зуб')
    elif base_feed_per_tooth not in (None, ''):
        feed_tooth = _positive(base_feed_per_tooth, 'Базовая подача на зуб')
        feed_tooth *= math.sqrt(diameter_value / 10) * _factor(operation_factor, 'Коэффициент операции')
    else:
        raise CalculationInputError('Задайте подачу на зуб или базовую подачу на зуб')

    ap = _optional_positive(depth_cut, 'Глубина ap')
    ae = _optional_positive(width_cut, 'Ширина ae')
    spindle_speed = speed * 1000 / (math.pi * diameter_value)
    feed_rate = feed_tooth * teeth * spindle_speed
    extra: dict[str, float] = {'feed_per_tooth': feed_tooth, 'number_teeth': teeth}
    warnings = list(_coolant_warnings(coolant, material))

    if ap is not None:
        extra['depth_cut'] = ap
    if ae is not None:
        extra['width_cut'] = ae
        if ae > diameter_value:
            warnings.append('Ширина ae не должна превышать диаметр фрезы без специальной стратегии.')
        # Формула радиального утонения применяется для ae < D/2. При полном
        # или большем погружении поправка равна единице.
        if ae < diameter_value / 2:
            denominator = math.sqrt(1 - (1 - 2 * ae / diameter_value) ** 2)
            extra['rctf'] = 1 / denominator
        else:
            extra['rctf'] = 1.0

    if ap is not None and ae is not None:
        # Q в формуле INNER — см³/мин; дополнительно сохраняем привычные мм³/мин.
        removal_mm3_min = ap * ae * feed_rate
        extra['material_removal_rate_mm3_min'] = removal_mm3_min
        extra['material_removal_rate_cm3_min'] = removal_mm3_min / 1000

    kienzle = _kienzle(
        kc1=kc1,
        mc=mc,
        chip_thickness=chip_thickness or feed_tooth,
        rake_angle=rake_angle,
    )
    calculated_power = None
    if kienzle and ap is not None and ae is not None:
        kc, hm = kienzle
        extra['chip_thickness'] = hm
        extra['specific_cutting_force'] = kc
        power_kw = extra['material_removal_rate_cm3_min'] * kc / 60000
        extra['cutting_power_kw'] = power_kw
        extra['cutting_moment_nm'] = power_kw * 9549 / spindle_speed
        calculated_power = power_kw

    machine_power_value = _optional_positive(machine_power, 'Мощность станка')
    warnings.extend(_machine_warnings(
        spindle_speed=spindle_speed,
        max_rpm=max_rpm,
        power_kw=machine_power_value,
        calculated_power_kw=calculated_power,
    ))
    max_rpm_value = _optional_positive(max_rpm, 'Максимальные обороты')
    if max_rpm_value is not None:
        extra['effective_spindle_speed'] = min(spindle_speed, max_rpm_value)
    return CalculationResult('milling', spindle_speed, feed_rate, speed, tuple(warnings), extra)


def calculate_turning(
    *,
    cutting_speed: object | None = None,
    base_cutting_speed: object | None = None,
    diameter: object,
    feed_per_revolution: object | None = None,
    roughness: object | None = None,
    nose_radius: object | None = None,
    depth_cut: object | None = None,
    approach_angle: object | None = None,
    rake_angle: object | None = None,
    kc1: object | None = None,
    mc: object | None = None,
    tool_factor: object | None = None,
    operation_factor: object | None = None,
    coolant_factor: object | None = None,
    stiffness_factor: object | None = None,
    stock_allowance: object | None = None,
    length_cut: object | None = None,
    max_rpm: object | None = None,
    machine_power: object | None = None,
    coolant: str | None = None,
    material: str | None = None,
) -> CalculationResult:
    """Расчёт точения по формулам скорости, Ra, Kienzle, Pc и проходов."""

    coolant_speed_factor = _coolant_speed_factor(coolant)
    if cutting_speed in (None, ''):
        base_speed = _positive(base_cutting_speed, 'Базовая скорость резания')
        speed = base_speed * _factor(tool_factor, 'Коэффициент инструмента') \
            * _factor(operation_factor, 'Коэффициент операции') \
            * _factor(coolant_factor, 'Коэффициент СОЖ', default=coolant_speed_factor) \
            * _factor(stiffness_factor, 'Коэффициент жёсткости')
    else:
        speed = _positive(cutting_speed, 'Скорость резания') \
            * _factor(coolant_factor, 'Коэффициент СОЖ', default=coolant_speed_factor)
    diameter_value = _positive(diameter, 'Диаметр детали')
    radius = _optional_positive(nose_radius, 'Радиус при вершине')
    roughness_value = _optional_positive(roughness, 'Требуемая шероховатость Ra')
    if feed_per_revolution not in (None, ''):
        feed = _positive(feed_per_revolution, 'Подача на оборот')
    elif roughness_value is not None and radius is not None:
        # Ra = f² * 1000 / (32*r*1.3), откуда f = sqrt(Ra*32*r/(1000*1.3)).
        feed = math.sqrt(roughness_value * 32 * radius / (1000 * 1.3))
    else:
        raise CalculationInputError('Задайте подачу на оборот или пару Ra и радиус при вершине')

    spindle_speed = speed * 1000 / (math.pi * diameter_value)
    feed_rate = feed * spindle_speed
    extra: dict[str, float] = {'feed_per_revolution': feed}
    warnings = list(_coolant_warnings(coolant, material))
    if radius is not None:
        extra['nose_radius'] = radius
        extra['predicted_roughness'] = feed ** 2 * 1000 / (32 * radius * 1.3)
    ap = _optional_positive(depth_cut, 'Глубина ap')
    if ap is not None:
        extra['depth_cut'] = ap

    angle = float(approach_angle if approach_angle not in (None, '') else 90)
    chip_thickness = feed * math.sin(math.radians(angle))
    kienzle = _kienzle(
        kc1=kc1,
        mc=mc,
        chip_thickness=chip_thickness,
        rake_angle=rake_angle,
    )
    calculated_power = None
    if kienzle and ap is not None:
        kc, hm = kienzle
        extra['chip_thickness'] = hm
        extra['specific_cutting_force'] = kc
        force = kc * ap * feed
        extra['cutting_force_n'] = force
        power_kw = force * speed / 60000
        extra['cutting_power_kw'] = power_kw
        extra['cutting_moment_nm'] = power_kw * 9549 / spindle_speed
        calculated_power = power_kw

    stock = _optional_positive(stock_allowance, 'Припуск')
    if stock is not None and ap is not None:
        passes = math.ceil(stock / ap)
        extra['passes'] = float(passes)
        if feed_rate > 0 and length_cut not in (None, ''):
            length = _positive(length_cut, 'Длина обработки')
            extra['time_per_pass_min'] = length / feed_rate
            extra['total_time_min'] = extra['time_per_pass_min'] * passes

    machine_power_value = _optional_positive(machine_power, 'Мощность станка')
    warnings.extend(_machine_warnings(
        spindle_speed=spindle_speed,
        max_rpm=max_rpm,
        power_kw=machine_power_value,
        calculated_power_kw=calculated_power,
    ))
    max_rpm_value = _optional_positive(max_rpm, 'Максимальные обороты')
    if max_rpm_value is not None:
        extra['effective_spindle_speed'] = min(spindle_speed, max_rpm_value)
    return CalculationResult('turning', spindle_speed, feed_rate, speed, tuple(warnings), extra)


def calculate_threading(
    *,
    cutting_speed: object,
    diameter: object,
    pitch: object,
    max_rpm: object | None = None,
    coolant: str | None = None,
    material: str | None = None,
) -> CalculationResult:
    """Расчёт резьбонарезания: подача на оборот равна шагу резьбы."""

    speed = _positive(cutting_speed, 'Скорость резания')
    diameter_value = _positive(diameter, 'Диаметр резьбы')
    pitch_value = _positive(pitch, 'Шаг резьбы')
    spindle_speed = speed * 1000 / (math.pi * diameter_value)
    warnings = list(_coolant_warnings(coolant, material))
    extra = {'pitch': pitch_value}
    max_rpm_value = _optional_positive(max_rpm, 'Максимальные обороты')
    if max_rpm_value is not None:
        extra['effective_spindle_speed'] = min(spindle_speed, max_rpm_value)
        if spindle_speed > max_rpm_value:
            warnings.append(f'Расчётные обороты превышают ограничение станка ({max_rpm_value:g} об/мин).')
    return CalculationResult('threading', spindle_speed, pitch_value * spindle_speed, speed, tuple(warnings), extra)
