"""
utils.py — вспомогательные функции для построения отчёта.

Все функции чистые: не читают файлы сами, принимают DataFrame/скаляры,
возвращают DataFrame/скаляры. Это упрощает тестирование.
"""
from __future__ import annotations

import pandas as pd


# ---------- Загрузка ----------

def load_csv(path: str, sep: str = ";") -> pd.DataFrame:
    """
    Читает CSV с учётом BOM (utf-8-sig) и разделителя ';'.
    Все колонки читаем как строки — типы приводим отдельно.
    """
    return pd.read_csv(path, sep=sep, encoding="utf-8-sig", dtype=str)


def parse_month_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Приводит колонку с месяцем (YYYY-MM-DD) к datetime.
    pandas.parse_dates с errors='coerce' — некорректные значения станут NaT.
    """
    df = df.copy()
    df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


def parse_amount_column(df: pd.DataFrame, column: str = "amount") -> pd.DataFrame:
    """amount → числовой тип (float). Ошибки → NaN."""
    df = df.copy()
    df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


# ---------- Цепочки проектов ----------

def build_project_chains(history: pd.DataFrame) -> dict[str, list[str]]:
    """
    Строит цепочки переименований из projects_history.

    На входе DataFrame с колонками:
        project_id, new_project_id, month
    На выходе dict: {старый_id: [старый_id, ..., новый_id]}

    Пример: 310 -> 311  ==>  {'310': ['310', '311']}
    """
    chains: dict[str, list[str]] = {}

    for _, row in history.iterrows():
        old_id = str(row["project_id"])
        new_id = str(row["new_project_id"])

        # Если old_id уже где-то в середине цепочки — дополняем её
        found = False
        for head, chain in chains.items():
            if old_id in chain:
                idx = chain.index(old_id)
                chains[head] = chain[: idx + 1] + [new_id]
                found = True
                break

        if not found:
            chains[old_id] = [old_id, new_id]

    return chains


def get_chain_for(project_id: str, chains: dict[str, list[str]]) -> list[str]:
    """Возвращает полную цепочку для project_id (или [project_id])."""
    for head, chain in chains.items():
        if project_id in chain:
            return chain
    return [project_id]


def get_current_project_id(chain: list[str]) -> str:
    """Последний (актуальный) ID в цепочке."""
    return chain[-1]


def chain_to_project_ids(chain: list[str]) -> str:
    """Склеивает цепочку в строку через '|' (как в отчёте)."""
    return "|".join(chain)


# ---------- Работа с works ----------

def aggregate_works_by_month(works: pd.DataFrame) -> pd.DataFrame:
    """
    Схлопывает разбитые платежи (например, 'первая часть' + 'вторая часть')
    в одну строку на (project_id, month).

    Также:
    - приводит label к нижнему регистру (для поиска 'стоп');
    - оставляет флаг is_stop.
    """
    df = works.copy()
    df["label"] = df["label"].fillna("").str.lower()
    df["is_stop"] = df["label"].str.contains("стоп", na=False)

    # Суммируем amount по (project_id, month), сохраняем max(is_stop)
    grouped = (
        df.groupby(["project_id", "month"], as_index=False)
        .agg(amount=("amount", "sum"), is_stop=("is_stop", "max"))
    )
    return grouped


def filter_works_before(works: pd.DataFrame, report_date: pd.Timestamp) -> pd.DataFrame:
    """
    Оставляет только месяцы строго до даты генерации отчёта.
    Это отсекает 'будущие' оплаты (как у 350 после 2025-09).
    """
    return works[works["month"] < report_date].copy()


def get_active_months(works: pd.DataFrame) -> list[pd.Timestamp]:
    """
    Возвращает отсортированный список месяцев с amount > 0.
    Месяцы-стопы (amount=0) в активные не попадают.
    """
    active = works[works["amount"] > 0]["month"].unique()
    return sorted(pd.to_datetime(active))


def get_stop_months(works: pd.DataFrame) -> set[pd.Timestamp]:
    """Множество месяцев, помеченных как стоп."""
    return set(works[works["is_stop"]]["month"].unique())


# ---------- Расчёт полётов ----------

def split_periods_by_stops(
    active_months: list[pd.Timestamp],
    stop_months: set[pd.Timestamp],
) -> list[list[pd.Timestamp]]:
    """
    Режет список активных месяцев на периоды в местах стопов.

    Логика: если между двумя соседними активными месяцами есть стоп —
    начинается новый период.
    """
    if not active_months:
        return []

    periods: list[list[pd.Timestamp]] = []
    current: list[pd.Timestamp] = [active_months[0]]

    for month in active_months[1:]:
        prev = current[-1]
        # есть ли стоп между prev и month?
        has_stop_between = any(prev < s < month for s in stop_months)
        if has_stop_between:
            periods.append(current)
            current = [month]
        else:
            current.append(month)

    periods.append(current)
    return periods


def calculate_flights_for_period(
    period: list[pd.Timestamp],
    stop_months: set[pd.Timestamp],
    term_months: int,
) -> list[dict]:
    """
    Считает полёты внутри одного непрерывного периода активности.

    Возвращает список dict с ключами:
        flight_no, flight_start, flight_end, last_active_month, has_stop
    """
    flights: list[dict] = []
    flight_no = 1
    current_start = period[0]

    while True:
        # Конец полёта: start + term_months - 1 месяц
        flight_end = current_start + pd.DateOffset(months=term_months) - pd.DateOffset(months=1)

        # Активные месяцы внутри полёта
        flight_months = [m for m in period if current_start <= m <= flight_end]
        if not flight_months:
            break

        last_active = max(flight_months)

        # Был ли стоп внутри полёта?
        has_stop = any(current_start <= s <= flight_end for s in stop_months)

        flights.append({
            "flight_no": flight_no,
            "flight_start": current_start,
            "flight_end": flight_end,
            "last_active_month": last_active,
            "has_stop": has_stop,
        })

        # Следующий полёт начинается с первого активного месяца после last_active
        next_months = [m for m in period if m > last_active]
        if not next_months:
            break

        current_start = next_months[0]
        flight_no += 1

    return flights


def calculate_flights_for_project(
    works: pd.DataFrame,
    term_months: int,
) -> list[dict]:
    """
    Полный расчёт полётов для проекта:
    1) режем на периоды по стопам,
    2) в каждом периоде считаем полёты (нумерация сбрасывается).
    """
    active_months = get_active_months(works)
    stop_months = get_stop_months(works)
    periods = split_periods_by_stops(active_months, stop_months)

    all_flights: list[dict] = []
    for period in periods:
        all_flights.extend(calculate_flights_for_period(period, stop_months, term_months))

    return all_flights


# ---------- Статусы ----------

def months_between(later: pd.Timestamp, earlier: pd.Timestamp) -> int:
    """Число полных месяцев между двумя датами."""
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def determine_status(
    flight: dict,
    has_next_flight: bool,
    project_type: str,
    report_date: pd.Timestamp,
    unknown_threshold_months: int = 3,
) -> str:
    """
    Определяет статус полёта.

    Приоритет:
      1. Разовый проект             → 'завершился (разовые работы)'
      2. Был стоп                   → 'отвал'
      3. Есть следующий полёт       → 'пролонгировано'
      4. last_active давно (< N мес) → 'непролонгировано'
      5. Иначе                      → 'неизвестно'
    """
    if project_type == "Разовый":
        return "завершился (разовые работы)"

    if flight["has_stop"]:
        return "отвал"

    if has_next_flight:
        return "пролонгировано"

    delta = months_between(report_date, flight["last_active_month"])
    if delta <= unknown_threshold_months:
        return "неизвестно"
    return "непролонгировано"


# ---------- Сборка отчёта ----------

def build_report(
    projects: pd.DataFrame,
    works: pd.DataFrame,
    terms: pd.DataFrame,
    chains: dict[str, list[str]],
    report_date: pd.Timestamp,
    unknown_threshold_months: int = 3,
) -> pd.DataFrame:
    """
    Главная функция: собирает итоговый DataFrame отчёта.

    Шаги:
      1. Фильтруем works до report_date.
      2. Для каждого проекта определяем term_months из справочника услуг.
      3. Объединяем works по всей цепочке проекта (для 310|311 и 320|321).
      4. Считаем полёты и статусы.
      5. Собираем строки отчёта.
    """
    # 1. Только прошедшие месяцы
    works = filter_works_before(works, report_date)

    # Справочник term_months по типу услуги
    term_map = dict(zip(terms["service_type"], terms["term_months"].astype(int)))

    # Приводим project_id к строке для merge
    projects = projects.copy()
    works = works.copy()
    projects["project_id"] = projects["project_id"].astype(str)
    works["project_id"] = works["project_id"].astype(str)

    # Какие project_id встречаются в works?
    all_project_ids = set(works["project_id"].unique())

    # Строим отчёт
    rows: list[dict] = []
    processed_chains: set[tuple[str, ...]] = set()

    for project_id in sorted(all_project_ids):
        chain = get_chain_for(project_id, chains)
        chain_key = tuple(chain)
        if chain_key in processed_chains:
            continue
        processed_chains.add(chain_key)

        current_id = get_current_project_id(chain)

        # Информация о текущем проекте
        proj_row = projects[projects["project_id"] == current_id]
        if proj_row.empty:
            # Проект есть в works, но нет в справочнике — пропускаем с предупреждением
            print(f"[WARN] Проект {current_id} отсутствует в projects.csv — пропущен")
            continue

        proj_row = proj_row.iloc[0]
        project_name = proj_row["project_name"]
        service_type = proj_row["service_type"]
        project_type = proj_row["project_type"]
        term_months = int(proj_row["term_months"]) if pd.notna(proj_row["term_months"]) \
            else term_map.get(service_type, 1)

        # Объединяем works по всей цепочке
        chain_works = works[works["project_id"].isin(chain)].copy()
        if chain_works.empty:
            continue

        # Агрегируем по месяцу (сумма по всей цепочке)
        chain_works = (
            chain_works.groupby("month", as_index=False)
            .agg(amount=("amount", "sum"), is_stop=("is_stop", "max"))
        )

        flights = calculate_flights_for_project(chain_works, term_months)
        if not flights:
            continue

        # Определяем статусы (следующий полёт известен заранее)
        for idx, flight in enumerate(flights):
            has_next = idx < len(flights) - 1
            status = determine_status(
                flight, has_next, project_type, report_date, unknown_threshold_months
            )

            rows.append({
                "client_id": current_id,
                "project_ids": chain_to_project_ids(chain),
                "project_name": project_name,
                "service_type": service_type,
                "term_months": term_months,
                "flight_no": flight["flight_no"],
                "flight_start": flight["flight_start"].strftime("%Y-%m-%d"),
                "flight_end": flight["flight_end"].strftime("%Y-%m-%d"),
                "last_active_month": flight["last_active_month"].strftime("%Y-%m-%d"),
                "status": status,
                "report_generated_at": report_date.strftime("%Y-%m-%d"),
            })

    return pd.DataFrame(rows)