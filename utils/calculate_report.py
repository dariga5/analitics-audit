"""
calculate_report.py — читает исходные CSV, строит отчёт и сохраняет report_fixed.csv.
"""
from pathlib import Path
import pandas as pd

from utils import (
    load_csv,
    parse_month_column,
    parse_amount_column,
    build_project_chains,
    aggregate_works_by_month,
    build_report,
)

BASE = Path(__file__).resolve().parent.parent
SOURCE = BASE / "source-data"

REPORT_DATE = pd.Timestamp("2025-09-01")  # дата генерации отчёта
UNKNOWN_THRESHOLD_MONTHS = 3             # порог "неизвестно"


def main() -> None:
    # --- 1. Загрузка ---
    projects = load_csv(SOURCE / "projects.csv")
    history = load_csv(SOURCE / "projects_history.csv")
    terms = load_csv(SOURCE / "service_terms.csv")
    works = load_csv(SOURCE / "works.csv")

    # --- 2. Приведение типов ---
    works = parse_month_column(works, "month")
    works = parse_amount_column(works, "amount")
    history = parse_month_column(history, "month")

    # --- 3. Агрегация (схлопываем разбитые платежи, ищем стопы) ---
    works = aggregate_works_by_month(works)

    # --- 4. Цепочки переименований ---
    chains = build_project_chains(history)
    print(f"Цепочки проектов: {chains}")

    # --- 5. Сборка отчёта ---
    report = build_report(
        projects=projects,
        works=works,
        terms=terms,
        chains=chains,
        report_date=REPORT_DATE,
        unknown_threshold_months=UNKNOWN_THRESHOLD_MONTHS,
    )

    # --- 6. Сортировка как в эталоне ---
    report = report.sort_values(
        ["client_id", "flight_start", "flight_no"],
        kind="stable",
    ).reset_index(drop=True)

    # --- 7. Сохранение ---
    out_path = SOURCE / "report_fixed.csv"
    report.to_csv(out_path, sep=";", index=False, encoding="utf-8-sig")
    print(f"Отчёт сохранён: {out_path} ({len(report)} строк)")


if __name__ == "__main__":
    main()