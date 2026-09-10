"""
compare_reports.py — сравнивает два отчёта и выводит расхождения.

Использование:
    python compare_reports.py report.csv report_fixed.csv
"""
import sys
from pathlib import Path
import pandas as pd


KEY_COLS = ["client_id", "project_ids", "flight_no"]


def load_report(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)
    df["flight_no"] = pd.to_numeric(df["flight_no"], errors="coerce")
    return df


def compare(a_path: str, b_path: str) -> int:
    a = load_report(a_path)
    b = load_report(b_path)

    # Приводим к единому порядку колонок
    cols = list(a.columns)
    b = b[cols]

    # Индексируем по ключу
    a_idx = a.set_index(KEY_COLS)
    b_idx = b.set_index(KEY_COLS)

    only_in_a = a_idx.index.difference(b_idx.index)
    only_in_b = b_idx.index.difference(a_idx.index)
    common = a_idx.index.intersection(b_idx.index)

    problems = 0

    if len(only_in_a):
        print(f"\n=== Строки только в {a_path} ({len(only_in_a)}) ===")
        print(a_idx.loc[only_in_a].to_string())
        problems += len(only_in_a)

    if len(only_in_b):
        print(f"\n=== Строки только в {b_path} ({len(only_in_b)}) ===")
        print(b_idx.loc[only_in_b].to_string())
        problems += len(only_in_b)

    # Сравнение значений по общим ключам
    diff_mask = (a_idx.loc[common] != b_idx.loc[common]).any(axis=1)
    diff_keys = common[diff_mask]

    if len(diff_keys):
        print(f"\n=== Расхождения в значениях ({len(diff_keys)}) ===")
        for key in diff_keys:
            print(f"\n--- {key} ---")
            left = a_idx.loc[key]
            right = b_idx.loc[key]
            for col in cols:
                if left[col] != right[col]:
                    print(f"  {col}: '{left[col]}' != '{right[col]}'")
        problems += len(diff_keys)

    if problems == 0:
        print("OK: отчёты идентичны.")
        return 0

    print(f"\nВсего расхождений: {problems}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python compare_reports.py <report_a.csv> <report_b.csv>")
        sys.exit(2)
    sys.exit(compare(sys.argv[1], sys.argv[2]))