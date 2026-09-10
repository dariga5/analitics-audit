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
    "last_active_month", "status", "report_generated_at",
]


def build_client_report(
    works_path: str | Path,
    client_id: str,
    report_generated_at: pd.Timestamp | str,
) -> pd.DataFrame:


    report_generated_at = pd.Timestamp(report_generated_at)

    # 1. Цепочка переименований
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

    # 4. Отсекаем будущие месяцы
    works = works[works["month"] < report_generated_at].copy()
    if works.empty:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    monthly = aggregate_by_month(works)

    # 5. Временная линия услуг
    timeline = get_service_timeline(chain)

    # 6. Полёты
    flights = split_into_flights(monthly, timeline)
    if not flights:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    # 7. Собираем DataFrame
    df = pd.DataFrame(flights)
    df["client_id"] = current_id
    df["project_ids"] = project_ids_str
    df["project_name"] = project["project_name"]
    df["report_generated_at"] = report_generated_at.strftime("%Y-%m-%d")

    for col in ("flight_start", "flight_end", "last_active_month"):
        df[col] = df[col].dt.strftime("%Y-%m-%d")

    return df[REPORT_COLUMNS]