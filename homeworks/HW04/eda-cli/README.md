# S04 – eda_cli: мини-EDA для CSV

Небольшое CLI-приложение и REST API для базового анализа CSV-файлов.
Используется в рамках Семинара 03 курса «Инженерия ИИ».

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) установлен в систему

## Инициализация проекта

В корне проекта (`homeworks/HW04/eda-cli`):

```bash
uv sync
```

Эта команда:

- создаст виртуальное окружение `.venv`;
- установит зависимости из `pyproject.toml` (pandas, matplotlib, fastapi, uvicorn, typer, pytest и др.);
- установит сам проект `eda-cli` в окружение.

## Зависимости

Все необходимые зависимости указаны в `pyproject.toml`:

- **fastapi** – веб-фреймворк для REST API
- **uvicorn[standard]** – ASGI-сервер для запуска FastAPI
- **pandas** – обработка CSV и анализ данных
- **matplotlib** – визуализация (гистограммы, тепловые карты)
- **typer** – CLI-фреймворк
- **python-multipart** – поддержка загрузки файлов в FastAPI
- **pytest** – тестирование

После выполнения `uv sync` все пакеты будут установлены автоматически.

## Запуск CLI

### Краткий обзор датасета

```bash
uv run eda-cli overview data/example.csv
```

Параметры:

- `--sep` – разделитель (по умолчанию `,`)
- `--encoding` – кодировка (по умолчанию `utf-8`)

Пример с кастомным разделителем:

```bash
uv run eda-cli overview data/example.csv --sep ";" --encoding "utf-8"
```

### Полный EDA-отчёт

```bash
uv run eda-cli report data/example.csv --out-dir reports
```

В результате в каталоге `reports/` появятся:

- `report.md` – основной отчёт в Markdown
- `summary.csv` – таблица статистики по колонкам
- `missing.csv` – пропуски по колонкам
- `correlation.csv` – корреляционная матрица (если есть числовые признаки)
- `top_categories/*.csv` – top-k категорий по строковым признакам
- `hist_*.png` – гистограммы числовых колонок
- `missing_matrix.png` – визуализация пропусков
- `correlation_heatmap.png` – тепловая карта корреляций

Параметры:

- `--sep` – разделитель
- `--encoding` – кодировка
- `--out-dir` – каталог для сохранения отчётов (по умолчанию `reports`)

## Запуск REST API

Для запуска веб-сервиса используется **uvicorn**:

```bash
uvicorn eda_cli.api:app --host 0.0.0.0 --port 8000 --reload
```

Параметры:

- `eda_cli.api:app` – путь к FastAPI-приложению (модуль `eda_cli.api`, объект `app`)
- `--host 0.0.0.0` – слушать на всех сетевых интерфейсах
- `--port 8000` – порт (по умолчанию 8000)
- `--reload` – автоперезагрузка при изменении кода (для разработки)

После запуска API будет доступно по адресу:

- **Основной адрес**: `http://localhost:8000`
- **Интерактивная документация (Swagger UI)**: `http://localhost:8000/docs`
- **Альтернативная документация (ReDoc)**: `http://localhost:8000/redoc`

### Доступные эндпоинты

1. **GET /** – корневой эндпоинт, возвращает информацию о сервисе
2. **POST /overview** – краткий обзор загруженного CSV-файла
3. **POST /report** – генерация полного EDA-отчёта с визуализациями

Пример использования через `curl`:

```bash
# Краткий обзор
curl -X POST "http://localhost:8000/overview" \
  -F "file=@data/example.csv" \
  -F "sep=," \
  -F "encoding=utf-8"

# Полный отчёт
curl -X POST "http://localhost:8000/report" \
  -F "file=@data/example.csv" \
  -F "sep=," \
  -F "encoding=utf-8"
```

## Тесты

Для запуска тестов используйте pytest:

```bash
uv run pytest -q
```

Или с более подробным выводом:

```bash
uv run pytest -v
```

## Структура проекта

```
eda-cli/
├── src/
│   └── eda_cli/
│       ├── __init__.py
│       ├── api.py          # FastAPI REST API
│       ├── cli.py          # CLI-команды (typer)
│       ├── core.py         # Логика EDA-анализа
│       └── viz.py          # Визуализация (matplotlib)
├── data/
│   └── example.csv         # Примеры данных
├── tests/
│   └── ...                 # Тесты
├── pyproject.toml          # Конфигурация и зависимости
├── uv.lock                 # Зафиксированные версии зависимостей
└── README.md               # Этот файл
```

## Примечания

- Для работы с CSV-файлами используется pandas
- Визуализации генерируются с помощью matplotlib
- API реализовано на FastAPI с автоматической генерацией документации
- CLI создан с помощью typer для удобного взаимодействия в терминале
- Проект использует uv для управления зависимостями и виртуальным окружением
