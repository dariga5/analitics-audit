"""
utils.py — вспомогательные утилиты.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SOURCE_DIR = Path(__file__).resolve().parent.parent / "source-data"


def read_csv(filename: str) -> pd.DataFrame:

    path = Path(filename)

    if not path.is_absolute() and path.parent == Path("."):
        path = SOURCE_DIR / path

    return pd.read_csv(
        path, sep=";", 
        encoding="utf-8-sig",
        dtype=str, 
        keep_default_na=False,
    )


# ---------- Загрузка источников данных ----------

def load_works(
    project_ids: str | list[str],
    works_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Читает works.csv, оставляет строки указанных проектов.
    project_ids: один id или список (для цепочек).
    works_path:  путь к works.csv. Если None — source-data/works.csv.
    """
    if isinstance(project_ids, str):
        project_ids = [project_ids]
    project_ids = [str(p) for p in project_ids]

    works = read_csv(works_path if works_path else "works.csv")
    works = works[works["project_id"].isin(project_ids)].copy()

    return works

def load_project(project_id: str) -> pd.Series | None:

    projects = read_csv("projects.csv")
    row = projects[projects["project_id"] == str(project_id)]
    if row.empty:
        return None

    return row.iloc[0]

def load_term_map() -> dict[str, int]:

    df = read_csv("service_terms.csv")

    return dict(zip(df["service_type"], df["term_months"].astype(int)))


# ---------- Парсинг типов ----------

def parse_amount(df: pd.DataFrame, column: str = 'amount') -> pd.DataFrame:
    df = df.copy()
    df[column] = pd.to_numeric(df[column], errors='coerce')

    return df

def parse_month(df: pd.DataFrame, column: str = 'month') -> pd.DataFrame:
    df = df.copy()
    df[column] = pd.to_datetime(df[column], errors='coerce')

    return df

def parse_label(df: pd.DataFrame, column: str = "label") -> pd.DataFrame:
    df = df.copy()
    df[column] = df[column].fillna("").astype(str).str.lower().str.strip()
    return df

# ---------- Агрегации ----------

#По месяцам
def aggregate_by_month(works: pd.DataFrame) -> pd.DataFrame:

    def combine_part(series):
        return "дробный платёж" if len(series) > 1 else "основная часть"

    def combine_label(series):
        parts = [str(x).strip().lower() for x in series if str(x).strip()]
        return " ".join(parts)

    works = parse_amount(works, "amount")

    monthly = (
        works.groupby("month", as_index=False)
        .agg(
            amount=("amount", "sum"),
            part=("part", combine_part),
            label=("label", combine_label),
        )
        .sort_values("month")
        .reset_index(drop=True)
    )

    monthly["is_stop"] = (monthly["amount"] == 0) | monthly["label"].str.contains("стоп", na=False)
    monthly["is_end"]  = monthly["label"].str.contains(r"\bend\b", na=False, regex=True)

    return monthly


# ---------- Внутрение функции ----------
def _next_special_after(monthly: pd.DataFrame, month: pd.Timestamp) -> str | None:
    """
    Если сразу после `month` в monthly идёт стоп-месяц или end-месяц —
    возвращает 'отвал' или 'отказ'. Иначе None.
    """
    later = monthly[monthly["month"] > month].sort_values("month")
    if later.empty:
        return None

    next_row = later.iloc[0]
    if next_row["is_end"]:
        return "отказ"
    if next_row["is_stop"]:
        return "отвал"
    return None


def _split_consecutive_runs(months: pd.Series) -> list[list[pd.Timestamp]]:
    """
    Разбивает отсортированный ряд месяцев на группы подряд идущих.
    """
    if len(months) == 0:
        return []

    runs: list[list[pd.Timestamp]] = [[months.iloc[0]]]
    for i in range(1, len(months)):
        prev, curr = months.iloc[i - 1], months.iloc[i]
        if curr == prev + pd.DateOffset(months=1):
            runs[-1].append(curr)
        else:
            runs.append([curr])
    return runs


def _flight_status(chunk_len: int, term_months: int, has_next: bool) -> str:

    if chunk_len < term_months:
        return "неизвестно"
    if has_next:
        return "пролонгировано"
    return "непролонгировано"


def _service_at(month: pd.Timestamp, timeline: list[dict]) -> dict:
    current = timeline[0]
    for entry in timeline:
        if entry["from"] is None or entry["from"] <= month:
            current = entry
        else:
            break
    return current


def _determine_status(
    chunk_len: int,
    term_months: int,
    has_next: bool,
    service_type: str,
    next_special: str | None,
) -> str:
    """
    Финальный статус куска. Приоритет:
        1. Разовый аудит                → 'завершился'
        2. Стоп/end сразу после куска   → 'отвал'/'отказ'
        3. Стандартная логика           → _flight_status
    """
    if service_type == "Разовый аудит":
        return "завершился (разовые работы)"
    if next_special:
        return next_special
    return _flight_status(chunk_len, term_months, has_next)

# ---------- Отслеживание изменений ----------

def build_project_chains() -> dict[str, list[str]]:
    """
    Строит цепочки переименований из projects_history.csv.

    """
    history = read_csv("projects_history.csv")

    edges: dict[str, str] = {}
    for _, row in history.iterrows():
        edges[str(row["project_id"])] = str(row["new_project_id"])

    new_ids = set(edges.values())
    heads = [old for old in edges if old not in new_ids]

    chains: dict[str, list[str]] = {}
    for head in heads:
        chain = [head]
        current = head
        while current in edges:
            current = edges[current]
            chain.append(current)
        for pid in chain:
            chains[pid] = chain

    return chains

def get_last_payment_month(works_path: str | Path | None = None) -> pd.Timestamp | None:
    """
    Возвращает самый поздний месяц из works.csv.

    Если файл пуст — None.
    Используется как дефолтная дата отчёта.
    """
    works = read_csv(works_path if works_path else "works.csv")
    if works.empty:
        return None
    months = pd.to_datetime(works["month"], errors="coerce")
    
    return months.max()

def get_project_chain(project_id: str) -> list[str]:
    """Цепочка для проекта или [project_id], если переименований не было."""
    chains = build_project_chains()
    return chains.get(str(project_id), [str(project_id)])



def get_service_timeline(project_ids: str | list[str]) -> list[dict]:
    """Временная линия услуг для проекта (или цепочки проектов)."""
    if isinstance(project_ids, str):
        project_ids = [project_ids]
    project_ids = [str(p) for p in project_ids]

    # Актуальный проект — последний в цепочке
    current_id = project_ids[-1]
    project = load_project(current_id)
    if project is None:
        return []

    term_map = load_term_map()
    changes = read_csv("service_changes.csv")
    changes = changes[changes["project_id"].isin(project_ids)].copy()

    if changes.empty:
        service = project["service_type"]
        return [{
            "from": None,
            "service_type": service,
            "term_months": term_map[service],
        }]

    changes = parse_month(changes, "month")
    changes = changes.sort_values("month").reset_index(drop=True)

    first = changes.iloc[0]
    timeline = [{
        "from": None,
        "service_type": first["old_service_type"],
        "term_months": term_map[first["old_service_type"]],
    }]
    for _, row in changes.iterrows():
        timeline.append({
            "from": row["month"],
            "service_type": row["new_service_type"],
            "term_months": term_map[row["new_service_type"]],
        })

    return timeline

def split_into_flights(monthly: pd.DataFrame, timeline: list[dict]) -> list[dict]:
    """
    Режет месячные платежи на полёты с учётом смены услуг и стопов/end.
    """
    # 1. Активные месяцы
    active_mask = (monthly["amount"] > 0) & ~monthly["is_stop"] & ~monthly["is_end"]
    months = monthly[active_mask]["month"].sort_values().reset_index(drop=True)
    if len(months) == 0:
        return []

    # 2. Услуга для каждого месяца
    services = [_service_at(m, timeline) for m in months]

    # 3. Разбиваем на runs (пропуск месяца или смена услуги)
    runs: list[dict] = []
    current = {"months": [months.iloc[0]], "service": services[0]}
    for i in range(1, len(months)):
        prev_m, curr_m = months.iloc[i - 1], months.iloc[i]
        prev_s, curr_s = services[i - 1], services[i]

        gap = curr_m != prev_m + pd.DateOffset(months=1)
        change = curr_s["service_type"] != prev_s["service_type"]

        if gap or change:
            runs.append(current)
            current = {"months": [curr_m], "service": curr_s}
        else:
            current["months"].append(curr_m)
    runs.append(current)

    # 4. Режем каждый run на куски по term_months
    flights: list[dict] = []
    for run in runs:
        term = run["service"]["term_months"]
        service_type = run["service"]["service_type"]
        chunk_months = run["months"]

        chunks_in_run: list[tuple[list, bool]] = []
        for start in range(0, len(chunk_months), term):
            chunk = chunk_months[start:start + term]
            has_next = start + term < len(chunk_months)
            chunks_in_run.append((chunk, has_next))

        for i, (chunk, has_next) in enumerate(chunks_in_run):
            is_last = i == len(chunks_in_run) - 1

            # Смотрим "после куска" только для последнего куска run
            next_special = (
                _next_special_after(monthly, chunk[-1]) if is_last else None
            )

            status = _determine_status(
                chunk_len=len(chunk),
                term_months=term,
                has_next=has_next,
                service_type=service_type,
                next_special=next_special,
            )

            flights.append({
                "flight_no": len(flights) + 1,
                "flight_start": chunk[0],
                "flight_end": chunk[0] + pd.DateOffset(months=term - 1),
                "last_active_month": chunk[-1],
                "service_type": service_type,
                "term_months": term,
                "status": status,
                "note": "требует уточнения" if status == "неизвестно" else "",
            })

    return flights