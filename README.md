# goreport

Инструмент для построения и сравнения отчётов по проектам.

- **Аналитика** — на Python + pandas: строит `report_fixed.csv` из исходных CSV.
- **Визуализация** — на Go: веб-сервис для сравнения двух отчётов.

---

## Содержание

1. [Структура проекта](#структура-проекта)
2. [Требования](#требования)
3. [Быстрый старт](#быстрый-старт)
4. [Аналитика (Python)](#аналитика-python)
5. [Веб-сервис (Go)](#веб-сервис-go)
6. [Исходные данные](#исходные-данные)
7. [Логика отчёта](#логика-отчёта)
8. [Известные ограничения](#известные-ограничения)

---

## Структура проекта

```
goreport/
├── source-data/                # исходные CSV + сгенерированный отчёт
│   ├── projects.csv
│   ├── projects_history.csv
│   ├── service_changes.csv
│   ├── service_terms.csv
│   ├── works.csv
│   ├── report.csv              # образец формата (не эталон значений)
│   └── report_fixed.csv        # результат работы аналитики
│
├── utils/                      # аналитические скрипты
│   ├── utils.py                # вспомогательные функции
│   ├── client_report.py        # сборка отчёта по одному клиенту (библиотека)
│   ├── report_generator.py     # CLI: отчёт по всем клиентам
│
├── visualization/              # веб-сервис на Go
│   ├── cmd/server/main.go      # точка входа
│   ├── internal/
│   │   ├── api/handlers.go     # HTTP-ручки
│   │   └── report/             # чтение CSV и сравнение
│   ├── pkg/models/report.go    # структуры данных
│   ├── static/                 # HTML/CSS/JS
│   └── go.mod
│
├── AUDIT.md                    # аудит задачи: проблемы, допущения, вопросы
└── README.md                   # этот файл
```

---

## Требования

| Инструмент | Версия | Для чего |
|-----------|--------|----------|
| Python | 3.10+ | аналитика |
| pandas | 2.0+ | работа с таблицами |
| Go | 1.21+ | веб-сервис |

Никаких внешних зависимостей в Go-проекте нет — только стандартная библиотека.

---

## Быстрый старт

```bash
# 1. Аналитика: сгенерировать отчёт
cd utils
python -m venv .venv              
.venv\Scripts\activate            
pip install pandas               
python report_generator.py <конечная дата>

# 2. Визуализация: запустить веб-сервис
cd ../visualization
go run ./cmd/server
# → http://localhost:8080
```

---

## Аналитика (Python)

### Установка окружения

**Windows (PowerShell):**

```powershell
cd utils
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pandas
```

**Linux / macOS:**

```bash
cd utils
python3 -m venv .venv
source .venv/bin/activate
pip install pandas
```

Первый запуск — только один раз. Дальше достаточно активировать venv:

```powershell
cd utils
.\.venv\Scripts\Activate.ps1
```

### Генерация отчёта

Основной скрипт — `report_generator.py`. Проходит по всем клиентам из `projects.csv`, строит отчёт для каждого и склеивает в один файл.

```powershell
cd utils
python report_generator.py <конечная дата>
```

**Аргументы:**

| Позиционный / флаг | Описание |
|--------------------|----------|
| `<report_generated_at>` | Дата отчёта `YYYY-MM-DD`. Учитываются месяцы строго до неё |
| `-o`, `--output` | Путь к выходному CSV. По умолчанию — `source-data/report_fixed.csv` |
| `--works` | Путь к `works.csv`. По умолчанию — `source-data/works.csv` |

**Примеры:**

```powershell
# Отчёт до 1 сентября 2025 — в дефолтный путь
python report_generator.py 2025-09-01

# Отчёт до 1 января 2025 — в отдельный файл
python report_generator.py 2025-01-01 -o ..\source-data\report_2025-01.csv

# Отчёт по другому набору работ
python report_generator.py 2025-09-01 --works ..\source-data\works_test.csv
```

**Вывод:**

```
Сохранено: T:\...\source-data\report_fixed.csv (17 строк, 11 клиентов)
```

### Использование как библиотеки

`client_report.py` — библиотечный модуль. Можно вызывать из своего кода:

```python
import pandas as pd
from client_report import build_client_report

df = build_client_report(
    works_path="works.csv",
    client_id="301",
    report_generated_at="2025-09-01",
)
print(df)
```

Возвращает `DataFrame` с колонками:
`client_id, project_ids, project_name, service_type, term_months,
flight_no, flight_start, flight_end, last_active_month, status, report_generated_at`.

---

## Веб-сервис (Go)

### Запуск

```powershell
cd visualization
go run ./cmd/server
```

Сервис поднимется на `http://localhost:8080`.

**Флаги:**

| Флаг | По умолчанию | Описание |
|------|--------------|----------|
| `-addr` | `:8080` | Адрес и порт |
| `-static` | автоопределение | Папка со статикой |

**Примеры:**

```powershell
# Другой порт
go run ./cmd/server -addr :9000

# Явная папка со статикой
go run ./cmd/server -static ./visualization/static
```

### API

| Метод | Путь | Что делает |
|-------|------|-----------|
| `GET` | `/api/health` | Проверка живости: `{"status":"ok"}` |
| `POST` | `/api/compare` | Сравнить два отчёта. Принимает `multipart/form-data` с полями `file_a` и `file_b` |

**Пример запроса:**

```bash
curl -X POST http://localhost:8080/api/compare \
  -F "file_a=@source-data/report.csv" \
  -F "file_b=@source-data/report_fixed.csv"
```

**Формат ответа:**

```json
{
  "only_in_a": [],
  "only_in_b": [],
  "different": [
    {
      "key": "301|301|2",
      "row_num_a": 1,
      "row_num_b": 1,
      "fields": [
        { "column": "last_active_month", "value_a": "2024-12-01", "value_b": "2024-11-01" }
      ]
    }
  ],
  "summary": {
    "total_a": 17,
    "total_b": 17,
    "only_in_a": 0,
    "only_in_b": 0,
    "different": 3,
    "same": 14
  }
}
```

### Как пользоваться UI

1. Откройте `http://localhost:8080`.
2. Перетащите первый CSV в левую зону.
3. Перетащите второй CSV в правую зону.
4. Нажмите «Сравнить».

Результат — три блока:

- **Только в «имя_файла_A»** — строки, которых нет в B.
- **Только в «имя_файла_B»** — строки, которых нет в A.
- **Расхождения** — строки с одинаковым ключом `(client_id, project_ids, flight_no)`, но разными значениями колонок.

В расхождениях для каждой строки показаны:

- ключ,
- номер строки в A и в B,
- только те колонки, которые отличаются, с парой «значение в A → значение в B».

### Сборка бинарника

```powershell
cd visualization
go build -o bin/server.exe ./cmd/server
.\bin\server.exe
```

---

## Исходные данные

Все CSV — с разделителем `;`, кодировка UTF-8 с BOM, первая строка — заголовок.

| Файл | Роль |
|------|------|
| `projects.csv` | Справочник проектов (текущее состояние) |
| `projects_history.csv` | Переименования проектов (310 → 311) |
| `service_changes.csv` | Смены типа услуги по проекту |
| `service_terms.csv` | Справочник: тип услуги → срок в месяцах |
| `works.csv` | Ежемесячные оплаты |
| `report.csv` | Образец формата отчёта (значения могут быть неверными) |
| `report_fixed.csv` | Результат работы `report_generator.py` |

Подробнее про данные и их особенности — см. `AUDIT.md`.

---

## Логика отчёта

**Флайт** — это окно длиной `term_months`, начинающееся с первого активного месяца.
Активный месяц — тот, где `amount > 0` и нет метки «стоп» / «end».

**Нарезка на флайты:**

1. Отсеиваем неактивные месяцы.
2. Режем ряд на непрерывные отрезки (пропуск месяца рвёт отрезок).
3. Смена услуги тоже рвёт отрезок (у каждой услуги свой `term_months`).
4. Каждый отрезок режется на куски по `term_months`.

**Статусы:**

| Условие | Статус |
|---------|--------|
| `service_type == "Разовый аудит"` | `завершился` |
| Сразу после куска — стоп (`amount=0` или `label~стоп`) | `отвал` |
| Сразу после куска — `label=end` | `отказ` |
| Длина < `term_months` | `неизвестно` |
| Длина = `term_months` и есть следующий кусок в том же отрезке | `пролонгировано` |
| Длина = `term_months` и кусок последний | `непролонгировано` |



## Разработка

### Проверка кода аналитики

```powershell
cd utils
python -c "from utils import *; print('ok')"
python report_generator.py 2025-09-01
```

### Проверка Go-сервиса

```powershell
cd visualization
go vet ./...
go build ./...
```

### Структура кода

**Python:**

- `utils.py` — чистые функции.
- `client_report.py` — библиотечный модуль, только `build_client_report`.
- `report_generator.py` — CLI-оркестратор.

**Go:**

- `pkg/models` — чистые структуры, без логики.
- `internal/report` — чтение CSV и сравнение. Не знает про HTTP.
- `internal/api` — тонкий слой: HTTP → вызов `report` → JSON.
- `cmd/server` — сборка зависимостей и запуск.
- `static/` — фронтенд на vanilla JS.

---

## Лицензия

Берите, мне не жалко