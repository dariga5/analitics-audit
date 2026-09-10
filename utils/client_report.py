"""
client_report.py — сборка отчёта по одному клиенту.

Библиотечный модуль. CLI живёт в report_generator.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils import (
    load_project,
    load_works,
    get_project_chain,
    get_service_timeline,
    get_last_payment_month,
    parse_amount,
    parse_month,
    parse_label,
    aggregate_by_month,
    split_into_flights,
)


REPORT_COLUMNS = [
    "client_id", "project_ids", "project_name",
    "service_type", "term_months",
    "flight_no", "flight_start", "flight_end",
    "last_active_month", "status", "note", "report_generated_at",
]


def build_client_report(
    works_path: str | Path,
    client_id: str,
    report_generated_at: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """
    Строит отчёт по одному клиенту.

    Параметры:
        works_path          — путь к works.csv
        client_id           — ID клиента (любое звено цепочки)
        report_generated_at — дата отчёта.
                              • Если задана явно — фильтруем `month < дата`.
                              • Если None — берём последний месяц из works
                                и фильтр НЕ применяем.

    Возвращает DataFrame с колонками REPORT_COLUMNS.

    Пустой DataFrame (с теми же колонками) — если данных нет.
    """
    # Запоминаем, задал ли пользователь дату явно,
    # ДО того как подменим None на реальное значение.
    user_provided_date = report_generated_at is not None

    # Если дата не задана — определяем последний месяц из works
    if not user_provided_date:
        report_generated_at = get_last_payment_month(works_path)
        if report_generated_at is None:
            raise ValueError("works.csv пуст — не могу определить дату отчёта")

    report_generated_at = pd.Timestamp(report_generated_at)

    # 1. Цепочка переименований (310 → 311, 320 → 321)
    chain = get_project_chain(client_id)
    current_id = chain[-1]
    project_ids_str = "|".join(chain)

    # 2. Справочник по актуальному id
    project = load_project(current_id)
    if project is None:
        raise ValueError(f"Проект {current_id} не найден в projects.csv")

    # 3. Сырые works по всей цепочке
    works = load_works(chain, works_path=works_path)
    if works.empty:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    works = parse_amount(works)
    works = parse_month(works)
    works = parse_label(works)

    # 4. Фильтр по дате — только если пользователь задал дату явно
    if user_provided_date:
        works = works[works["month"] < report_generated_at].copy()
        if works.empty:
            return pd.DataFrame(columns=REPORT_COLUMNS)

    # 5. Агрегация по месяцам (дробные платежи складываются)
    monthly = aggregate_by_month(works)

    # 6. Временная линия услуг (смена услуги разрывает полёт)
    timeline = get_service_timeline(chain)

    # 7. Полёты
    flights = split_into_flights(monthly, timeline)
    if not flights:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    # 8. Собираем итоговый DataFrame
    df = pd.DataFrame(flights)
    
    df["client_id"] = current_id
    df["project_ids"] = project_ids_str
    df["project_name"] = project["project_name"]
    df["report_generated_at"] = report_generated_at.strftime("%Y-%m-%d")

    # 9. Форматирование дат
    for col in ("flight_start", "flight_end", "last_active_month"):
        df[col] = df[col].dt.strftime("%Y-%m-%d")

    return df[REPORT_COLUMNS]