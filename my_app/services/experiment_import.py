"""Проверка и импорт CSV-файлов с результатами экспериментов."""

import csv
import hashlib
import io
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from werkzeug.datastructures import FileStorage

from my_app.extensions import db
from my_app.models import Coating, Experiment, Material, Tool


EXPERIMENT_HEADERS = (
    'external_id', 'material', 'tool', 'coating', 'spindle_speed', 'feed_table',
    'depth_cut', 'width_cut', 'length_path', 'durability', 'data_experiment',
)
WEAR_HEADERS = ('external_id', 'length', 'wear')
MAX_ISSUES_IN_SUMMARY = 50

EXPERIMENT_HEADER_ALIASES = {
    'external_id': {'external_id', 'experiment_id', 'идентификатор_эксперимента', 'номер_эксперимента'},
    'material': {'material', 'материал', 'обрабатываемый_материал'},
    'tool': {'tool', 'инструмент', 'режущий_инструмент'},
    'coating': {'coating', 'покрытие', 'покрытие_инструмента'},
    'spindle_speed': {'spindle_speed', 'обороты', 'обороты_шпинделя', 'частота_вращения'},
    'feed_table': {'feed_table', 'подача', 'подача_мм_мин'},
    'depth_cut': {'depth_cut', 'глубина_резания', 'глубина_ap'},
    'width_cut': {'width_cut', 'ширина_резания', 'ширина_ae'},
    'length_path': {'length_path', 'длина_обработки', 'длина_пути'},
    'durability': {'durability', 'стойкость', 'стойкость_инструмента'},
    'data_experiment': {'data_experiment', 'date', 'дата', 'дата_эксперимента'},
}
WEAR_HEADER_ALIASES = {
    'external_id': {'external_id', 'experiment_id', 'идентификатор_эксперимента', 'номер_эксперимента'},
    'length': {'length', 'длина', 'пройденный_путь', 'длина_пути'},
    'wear': {'wear', 'износ', 'износ_мм'},
}


class ImportFileError(ValueError):
    """Файл невозможно прочитать до проверки строк."""


@dataclass(frozen=True)
class ImportIssue:
    source: str
    row: int | None
    message: str

    def display(self) -> str:
        row_hint = f', строка {self.row}' if self.row else ''
        return f'{self.source}{row_hint}: {self.message}'


@dataclass
class ImportPreview:
    experiment_rows: int = 0
    wear_rows: int = 0
    experiments: list[dict[str, Any]] = field(default_factory=list)
    wear_measurements: list[dict[str, Any]] = field(default_factory=list)
    issues: list[ImportIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.issues)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def issues_for_display(self) -> list[ImportIssue]:
        return self.issues[:MAX_ISSUES_IN_SUMMARY]


def _normalise_header(value: str | None) -> str:
    return (value or '').lstrip('\ufeff').strip().lower().replace('-', '_').replace(' ', '_')


def _lookup_key(value: str | None) -> str:
    return (value or '').strip()


def _decode_csv(data: bytes, source: str) -> str:
    for encoding in ('utf-8-sig', 'cp1251'):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportFileError(f'{source}: поддерживаются кодировки UTF-8 и Windows-1251.')


def _read_csv(path: str, source: str) -> tuple[list[tuple[int, dict[str, str | None]]], list[str]]:
    try:
        with open(path, 'rb') as csv_file:
            text = _decode_csv(csv_file.read(), source)
    except OSError as error:
        raise ImportFileError(f'{source}: не удалось открыть сохранённый файл.') from error

    if not text.strip():
        raise ImportFileError(f'{source}: файл пуст.')

    try:
        reader = csv.DictReader(io.StringIO(text), dialect=csv.Sniffer().sniff(text[:4096], delimiters=';,'))
    except csv.Error:
        delimiter = ';' if text[:4096].count(';') >= text[:4096].count(',') else ','
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        raise ImportFileError(f'{source}: не найдена строка заголовков.')

    rows: list[tuple[int, dict[str, str | None]]] = []
    for row_number, row in enumerate(reader, start=2):
        if None in row:
            raise ImportFileError(f'{source}, строка {row_number}: число значений не соответствует заголовкам.')
        if any((value or '').strip() for value in row.values()):
            rows.append((row_number, row))
    return rows, fieldnames


def _find_columns(fieldnames: list[str], aliases: dict[str, set[str]], source: str, issues: list[ImportIssue]) -> dict[str, str]:
    aliases_to_name = {
        _normalise_header(alias): canonical
        for canonical, possible_names in aliases.items()
        for alias in possible_names
    }
    columns: dict[str, str] = {}
    for fieldname in fieldnames:
        canonical = aliases_to_name.get(_normalise_header(fieldname))
        if canonical is None:
            continue
        if canonical in columns:
            issues.append(ImportIssue(source, 1, f'столбец «{canonical}» указан дважды.'))
        else:
            columns[canonical] = fieldname
    for column in aliases:
        if column not in columns:
            issues.append(ImportIssue(source, 1, f'не найден обязательный столбец «{column}».'))
    return columns


def _as_float(value: str | None, column: str, source: str, row_number: int, issues: list[ImportIssue], *, positive: bool = False) -> float | None:
    text = _lookup_key(value).replace('\xa0', '').replace(' ', '').replace(',', '.')
    try:
        number = float(text)
    except ValueError:
        issues.append(ImportIssue(source, row_number, f'«{column}» должно быть числом.'))
        return None
    if positive and number <= 0:
        issues.append(ImportIssue(source, row_number, f'«{column}» должно быть больше нуля.'))
        return None
    if not positive and number < 0:
        issues.append(ImportIssue(source, row_number, f'«{column}» не может быть отрицательным.'))
        return None
    return number


def _as_date(value: str | None, source: str, row_number: int, issues: list[ImportIssue]):
    text = _lookup_key(value)
    for date_format in ('%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    issues.append(ImportIssue(source, row_number, '«data_experiment» должно иметь формат ГГГГ-ММ-ДД или ДД.ММ.ГГГГ.'))
    return None


def _reference_maps() -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    return (
        {_lookup_key(item.name): item.id for item in db.session.scalars(db.select(Material)).all()},
        {_lookup_key(item.name): item.id for item in db.session.scalars(db.select(Tool)).all()},
        {_lookup_key(item.name): item.id for item in db.session.scalars(db.select(Coating)).all()},
    )


def validate_import_files(experiments_path: str, wear_path: str | None = None) -> ImportPreview:
    """Проверяет оба CSV и возвращает данные, готовые для одной транзакции."""
    preview = ImportPreview()
    experiment_rows, experiment_headers = _read_csv(experiments_path, 'Файл экспериментов')
    preview.experiment_rows = len(experiment_rows)
    experiment_columns = _find_columns(
        experiment_headers, EXPERIMENT_HEADER_ALIASES, 'Файл экспериментов', preview.issues,
    )
    if not preview.experiment_rows:
        preview.issues.append(ImportIssue('Файл экспериментов', None, 'нет строк с данными.'))
    if len(experiment_columns) == len(EXPERIMENT_HEADERS):
        material_map, tool_map, coating_map = _reference_maps()
        seen_external_ids: set[str] = set()
        for row_number, row in experiment_rows:
            issue_count = len(preview.issues)
            external_id = _lookup_key(row[experiment_columns['external_id']])
            if not external_id:
                preview.issues.append(ImportIssue('Файл экспериментов', row_number, 'не задан «external_id».'))
            elif len(external_id) > 64:
                preview.issues.append(ImportIssue('Файл экспериментов', row_number, '«external_id» длиннее 64 символов.'))
            elif external_id in seen_external_ids:
                preview.issues.append(ImportIssue('Файл экспериментов', row_number, f'повторяется «external_id» {external_id!r}.'))
            else:
                seen_external_ids.add(external_id)

            material_name = _lookup_key(row[experiment_columns['material']])
            tool_name = _lookup_key(row[experiment_columns['tool']])
            coating_name = _lookup_key(row[experiment_columns['coating']])
            material_id = material_map.get(material_name)
            tool_id = tool_map.get(tool_name)
            coating_id = coating_map.get(coating_name)
            if material_id is None:
                preview.issues.append(ImportIssue('Файл экспериментов', row_number, f'материал «{material_name}» не найден.'))
            if tool_id is None:
                preview.issues.append(ImportIssue('Файл экспериментов', row_number, f'инструмент «{tool_name}» не найден.'))
            if coating_id is None:
                preview.issues.append(ImportIssue('Файл экспериментов', row_number, f'покрытие «{coating_name}» не найдено.'))

            values = {
                'spindle_speed': _as_float(row[experiment_columns['spindle_speed']], 'spindle_speed', 'Файл экспериментов', row_number, preview.issues, positive=True),
                'feed_table': _as_float(row[experiment_columns['feed_table']], 'feed_table', 'Файл экспериментов', row_number, preview.issues, positive=True),
                'depth_cut': _as_float(row[experiment_columns['depth_cut']], 'depth_cut', 'Файл экспериментов', row_number, preview.issues),
                'width_cut': _as_float(row[experiment_columns['width_cut']], 'width_cut', 'Файл экспериментов', row_number, preview.issues),
                'length_path': _as_float(row[experiment_columns['length_path']], 'length_path', 'Файл экспериментов', row_number, preview.issues),
                'durability': _as_float(row[experiment_columns['durability']], 'durability', 'Файл экспериментов', row_number, preview.issues),
                'data_experiment': _as_date(row[experiment_columns['data_experiment']], 'Файл экспериментов', row_number, preview.issues),
            }
            if len(preview.issues) == issue_count:
                preview.experiments.append({
                    'external_id': external_id,
                    'material_id': material_id,
                    'tool_id': tool_id,
                    'coating_id': coating_id,
                    **values,
                })

        incoming_ids = [row['external_id'] for row in preview.experiments]
        if incoming_ids:
            existing_ids = set(db.session.scalars(
                db.select(Experiment.external_id).where(Experiment.external_id.in_(incoming_ids))
            ).all())
            for row_number, row in experiment_rows:
                external_id = _lookup_key(row[experiment_columns['external_id']])
                if external_id in existing_ids:
                    preview.issues.append(ImportIssue('Файл экспериментов', row_number, f'эксперимент с «external_id» {external_id!r} уже существует.'))
            if existing_ids:
                preview.experiments = [row for row in preview.experiments if row['external_id'] not in existing_ids]

    valid_experiment_ids = {row['external_id'] for row in preview.experiments}
    if wear_path:
        wear_rows, wear_headers = _read_csv(wear_path, 'Файл износа')
        preview.wear_rows = len(wear_rows)
        wear_columns = _find_columns(wear_headers, WEAR_HEADER_ALIASES, 'Файл износа', preview.issues)
        if not preview.wear_rows:
            preview.issues.append(ImportIssue('Файл износа', None, 'нет строк с данными.'))
        if len(wear_columns) == len(WEAR_HEADERS):
            seen_measurements: set[tuple[str, float, float]] = set()
            for row_number, row in wear_rows:
                issue_count = len(preview.issues)
                external_id = _lookup_key(row[wear_columns['external_id']])
                if external_id not in valid_experiment_ids:
                    preview.issues.append(ImportIssue('Файл износа', row_number, f'«external_id» {external_id!r} отсутствует среди корректных экспериментов.'))
                length = _as_float(row[wear_columns['length']], 'length', 'Файл износа', row_number, preview.issues)
                wear = _as_float(row[wear_columns['wear']], 'wear', 'Файл износа', row_number, preview.issues)
                if length is not None and wear is not None:
                    key = (external_id, length, wear)
                    if key in seen_measurements:
                        preview.issues.append(ImportIssue('Файл износа', row_number, 'повторяется точка измерения износа.'))
                    else:
                        seen_measurements.add(key)
                if len(preview.issues) == issue_count:
                    preview.wear_measurements.append({'external_id': external_id, 'length': length, 'wear': wear})
    return preview


def save_uploaded_import_files(
    experiments_file: FileStorage,
    wear_file: FileStorage | None,
    upload_root: str,
    max_file_size: int,
) -> tuple[str, str | None, str]:
    """Сохраняет файлы в закрытый каталог с непредсказуемым именем и возвращает хеш."""
    batch_directory = os.path.abspath(os.path.join(upload_root, uuid.uuid4().hex))
    root_directory = os.path.abspath(upload_root)
    if os.path.commonpath([batch_directory, root_directory]) != root_directory:
        raise ImportFileError('Не удалось подготовить каталог загрузки.')
    os.makedirs(batch_directory, exist_ok=False)

    def save_file(file_storage: FileStorage, filename: str) -> tuple[str, bytes]:
        content = file_storage.read(max_file_size + 1)
        if len(content) > max_file_size:
            raise ImportFileError(f'Файл «{file_storage.filename}» превышает допустимый размер.')
        if not content:
            raise ImportFileError(f'Файл «{file_storage.filename}» пуст.')
        path = os.path.join(batch_directory, filename)
        with open(path, 'wb') as output_file:
            output_file.write(content)
        return path, content

    try:
        experiments_path, experiments_content = save_file(experiments_file, 'experiments.csv')
        wear_path = None
        wear_content = b''
        if wear_file and wear_file.filename:
            wear_path, wear_content = save_file(wear_file, 'wear_measurements.csv')
        checksum = hashlib.sha256(experiments_content + b'\x00' + wear_content).hexdigest()
        return experiments_path, wear_path, checksum
    except Exception:
        shutil.rmtree(batch_directory, ignore_errors=True)
        raise


def issues_summary(preview: ImportPreview) -> str | None:
    if not preview.issues:
        return None
    lines = [issue.display() for issue in preview.issues_for_display]
    if preview.error_count > len(lines):
        lines.append(f'… и ещё {preview.error_count - len(lines)} ошибок.')
    return '\n'.join(lines)


def csv_template(kind: str, language: str = 'technical') -> str:
    """Генерирует совместимый с Excel CSV-шаблон с разделителем `;`."""
    rows_by_kind = {
        'experiments': [
            (('Идентификатор эксперимента', 'Материал', 'Инструмент', 'Покрытие', 'Обороты шпинделя', 'Подача', 'Глубина ap', 'Ширина ae', 'Длина пути', 'Стойкость', 'Дата эксперимента') if language == 'ru' else EXPERIMENT_HEADERS),
            ('EXP-001', 'Сталь 40Х', 'Фреза 10 мм', 'TiN', '1200', '240', '1', '5', '500', '35.5', '2026-08-29'),
        ],
        'wear': [
            (('Идентификатор эксперимента', 'Длина пути', 'Износ') if language == 'ru' else WEAR_HEADERS),
            ('EXP-001', '100', '0.03'),
        ],
    }
    if kind not in rows_by_kind:
        raise KeyError(kind)
    output = io.StringIO(newline='')
    writer = csv.writer(output, delimiter=';')
    writer.writerows(rows_by_kind[kind])
    return output.getvalue()
