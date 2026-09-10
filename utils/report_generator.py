"""
report_generator.py — собирает отчёт по всем клиентам.

Использование:
    python report_generator.py                          # все данные, без фильтра
    python report_generator.py 2025-09-01               # фильтр: месяц < 2025-09-01
    python report_generator.py 2025-09-01 -o out.csv
    python report_generator.py --works ./works_custom.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from utils import (
    SOURCE_DIR,
    read_csv,
    build_project_chains,
    get_last_payment_month,
)
from client_report import build_client_report, REPORT_COLUMNS


def find_all_client_chains() -> list[list[str]]:
    """
    Возвращает уникальные цепочки клиентов из projects.csv.

    Пример: [['301'], ['302'], ..., ['310', '311'], ['320', '321'], ['330'], ...]

    Цепочки вида ['310', '311'] и ['311'] не дублируются — мы отслеживаем
    уже встреченные кортежи в `seen`.
    """
    projects = read_csv("projects.csv")
    chains_map = build_project_chains()

    seen: set[tuple[str, ...]] = set()
    result: list[list[str]] = []

    for pid in projects["project_id"].astype(str):
        chain = chains_map.get(pid, [pid])
        key = tuple(chain)
        if key in seen:
            continue
        seen.add(key)
        result.append(chain)

    return result


def generate_full_report(
    works_path: str | Path,
    report_generated_at: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """
    Проходит по всем клиентам из projects.csv, строит отчёт для каждого,
    склеивает в один DataFrame.

    Параметры:
        works_path          — путь к works.csv
        report_generated_at — дата отчёта.
                              • Если задана — фильтр `month < дата`.
                              • Если None — все данные без фильтра.

    Пустые отчёты (нет оплат) не попадают в результат.
    """
    chains = find_all_client_chains()
    frames: list[pd.DataFrame] = []

    for chain in chains:
        try:
            df = build_client_report(
                works_path=works_path,
                client_id=chain[0],
                report_generated_at=report_generated_at,
            )
        except ValueError as e:
            print(f"[WARN] {e}", file=sys.stderr)
            continue

        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    return pd.concat(frames, ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Собирает отчёт по всем клиентам из projects.csv."
    )
    parser.add_argument(
        "report_generated_at",
        nargs="?",
        default=None,
        help="Дата отчёта YYYY-MM-DD. "
             "Если не указана — берётся последний месяц из works.csv, "
             "фильтр по дате НЕ применяется.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Путь к выходному CSV. По умолчанию — source-data/report_fixed.csv",
    )
    parser.add_argument(
        "--works",
        default=None,
        help="Путь к works.csv (по умолчанию — source-data/works.csv)",
    )
    args = parser.parse_args()

    output_path = (
        Path(args.output) if args.output
        else SOURCE_DIR / "report_fixed.csv"
    )
    works_path = args.works if args.works else "works.csv"

    # Диагностика — если пользователь не задал дату, покажем,
    # какую используем в отчёте (и что фильтр НЕ применяется).
    if args.report_generated_at is None:
        last = get_last_payment_month(works_path)
        if last is None:
            print("Ошибка: works.csv пуст — не могу определить дату отчёта",
                  file=sys.stderr)
            return 1
        print(
            f"report_generated_at не указан — "
            f"использую последний месяц {last.strftime('%Y-%m-%d')} "
            f"без фильтра",
            file=sys.stderr,
        )

    # Передаём «как есть» — None означает «без фильтра»,
    # явная дата — «отфильтровать month < дата».
    # Разбором занимается build_client_report.
    df = generate_full_report(
        works_path=works_path,
        report_generated_at=args.report_generated_at,
    )

    if df.empty:
        print("Отчёт пуст — ничего не сохраняем.", file=sys.stderr)
        return 0

    df.to_csv(output_path, sep=";", index=False, encoding="utf-8-sig")
    print(
        f"Сохранено: {output_path} "
        f"({len(df)} строк, {df['client_id'].nunique()} клиентов)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())