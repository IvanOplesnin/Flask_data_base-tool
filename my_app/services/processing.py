"""Единый реестр поддерживаемых видов обработки.

Новые операции добавляются сюда только после появления формулы и набора
валидируемых входных параметров. Это не позволяет показать пользователю
пустую форму, которая выглядит как готовый калькулятор.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingDefinition:
    key: str
    label: str
    description: str
    available: bool = True


PROCESSING_TYPES: tuple[ProcessingDefinition, ...] = (
    ProcessingDefinition('turning', 'Точение', 'Расчёт скорости, подачи и глубины точения'),
    ProcessingDefinition('milling', 'Фрезерование', 'Расчёт оборотов, подачи и съёма материала'),
    ProcessingDefinition('threading', 'Резьбонарезание', 'Расчёт оборотов с учётом шага резьбы'),
)

# Эти операции пока не выводятся в рабочий выбор: для них ещё нет утверждённых
# формул и полноценной модели инструмента.
FUTURE_PROCESSING_TYPES: tuple[ProcessingDefinition, ...] = (
    ProcessingDefinition('drilling', 'Сверление', 'Будет добавлено после утверждения формул', False),
    ProcessingDefinition('grinding', 'Шлифование', 'Будет добавлено после утверждения формул', False),
    ProcessingDefinition('planing', 'Строгание', 'Будет добавлено после утверждения формул', False),
    ProcessingDefinition('broaching', 'Протягивание', 'Будет добавлено после утверждения формул', False),
    ProcessingDefinition('mortising', 'Долбление', 'Будет добавлено после утверждения формул', False),
)

PROCESSING_BY_KEY = {item.key: item for item in (*PROCESSING_TYPES, *FUTURE_PROCESSING_TYPES)}
AVAILABLE_PROCESSING_KEYS = frozenset(item.key for item in PROCESSING_TYPES if item.available)


def get_processing(processing_type: str) -> ProcessingDefinition | None:
    """Возвращает описание операции или ``None`` для неизвестного ключа."""

    return PROCESSING_BY_KEY.get(processing_type)


def is_available_processing(processing_type: str) -> bool:
    return processing_type in AVAILABLE_PROCESSING_KEYS

