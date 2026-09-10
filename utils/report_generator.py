"""
report_generator.py — собирает отчёт по всем клиентам.
Использование:
    python utils/report_generator.py 2025-09-01
    python utils/report_generator.py 2025-09-01 -o ../source-data/report_fixed.csv
    python utils/report_generator.py 2025-09-01 --works ./works_custom.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from utils import SOURCE_DIR, read_csv, build_project_chains
from client_report import build_client_report, REPORT_COLUMNS


def find_all_client_chains() -> list[list[str]]:
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
    report_generated_at: pd.Timestamp | str,
) -> pd.DataFrame:
    """
    Проходит по всем клиентам из projects.csv, строит отчёт для каждого,
    склеивает в один DataFrame.

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
        help="Дата отчёта YYYY-MM-DD (месяцы строго до неё)",
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