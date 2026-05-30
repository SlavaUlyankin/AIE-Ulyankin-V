# Прогноз оттока клиентов телеком-оператора

В этой папке находится итоговый мини-проект по курсу «Инженерия Искусственного Интеллекта».

---

## 1. Паспорт проекта

- **Название проекта:** Сервис прогнозирования оттока клиентов (Churn Prediction)
- **Автор:** `Ульянкин Вячеслав Игоревич`
- **Группа:** `ИКБО-30-24`
- **Контакт:** `slava.ulyankin@gmail.com`

- **Краткое описание:**
  Бинарная классификация: предсказываем, уйдёт ли клиент телеком-оператора (churn = 1).
  Данные: IBM Telco Customer Churn (Kaggle, 7 043 клиента, 19 признаков).
  Финальная модель: CatBoostClassifier, обученная с подбором гиперпараметров.
  Результат — REST API на FastAPI, принимающий профиль клиента и возвращающий вероятность оттока.

---

## 2. Структура проекта

```
project/
├── README.md               — этот файл
├── report.md               — отчёт: задача, данные, модели, результаты
├── self-checklist.md       — самопроверка по 10 критериям курса
├── requirements.txt        — зависимости Python
├── Dockerfile              — сборка Docker-образа
├── docker-compose.yml      — локальный запуск через Compose
├── pytest.ini              — настройки pytest
├── run.py                  — точка входа (без Docker)
├── .gitignore
├── notebooks/
│   ├── 01_eda.ipynb        — EDA и предобработка (чеклист 3)
│   └── 02_models.ipynb     — Baseline vs CatBoost, сравнение (чеклист 4)
├── src/
│   ├── config.py           — настройки из .env (чеклист 7)
│   ├── data/
│   │   └── preprocessor.py — пайплайн предобработки (чеклист 5)
│   ├── models/
│   │   └── predictor.py    — загрузка модели и инференс (чеклист 2)
│   └── service/
│       ├── main.py         — FastAPI: /health, /predict, логи (чеклист 1, 8)
│       ├── schemas.py      — Pydantic-модели запроса и ответа
│       └── logger.py       — настройка logging
├── data/
│   ├── raw/                — исходный CSV (не коммитить)
│   └── processed/          — train/val/test после EDA
├── artifacts/              — model.pkl, encoders.pkl, model_meta.json
├── configs/
│   └── .env.example        — шаблон переменных окружения (чеклист 7)
├── tests/
│   └── test_predictor.py   — 24 теста (чеклист 1)
└── logs/                   — логи сервиса (не коммитить)
```

---

## 3. Требования и установка

### 3.1. Требования

- Python `>= 3.11`
- pip

### 3.2. Установка окружения

```bash
# Перейти в папку проекта
cd project

# Создать виртуальное окружение
python -m venv .venv

# Активировать:
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# Установить зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Создать .env из шаблона и заполнить API_KEY
cp configs/.env.example .env
```

Открой `.env` и замени `your_key_here` на любую строку (например, `secret123`).

### 3.3. Подготовка данных и модели

Перед запуском сервиса нужно обучить модель:

```bash
# 1. Скачай датасет с https://www.kaggle.com/datasets/blastchar/telco-customer-churn
#    Положи файл: data/raw/WA_Fn-UseC_-Telco-Customer-Churn.csv

# 2. Запусти ноутбуки по порядку (в Jupyter):
jupyter notebook

# notebooks/01_eda.ipynb  → создаст data/processed/ и artifacts/preprocessor.pkl
# notebooks/02_models.ipynb → создаст artifacts/model.pkl и artifacts/model_meta.json
```

---

## 4. Как запустить проект

### 4.1. Вручную (без Docker)

```bash
cd project
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

python run.py
```

Сервис: http://localhost:8000

### 4.2. Через Docker

```bash
# Сборка образа
docker build -t churn-service .

# Запуск
docker run --env-file .env -p 8000:8000 churn-service
```

### 4.3. Через Docker Compose (рекомендуется)

```bash
docker compose up --build
```

Для запуска в фоне: `docker compose up -d`
Просмотр логов: `docker compose logs -f`
Остановка: `docker compose down`

**Эндпоинты:**

| Метод | URL | Аутентификация |
|-------|-----|---------------|
| `GET` | `/health` | не требуется |
| `POST` | `/predict` | `X-API-Key: <ключ из .env>` |
| `GET` | `/docs` | не требуется (Swagger UI) |

---

## 5. Данные

- **Источник:** IBM Telco Customer Churn — https://www.kaggle.com/datasets/blastchar/telco-customer-churn
- **Размер:** 7 043 строки, 21 признак, ~977 КБ
- **Хранение:** в репозитории только `data/processed/` (обработанные сплиты). Исходный CSV скачивается отдельно.
- **Подготовка:** запусти `notebooks/01_eda.ipynb` — он создаёт все нужные файлы.

---

## 6. Тесты

```bash
cd project
# Windows:
.venv\Scripts\activate

pytest tests/ -v
```

24 теста в 4 классах. Работают без файлов модели (используют mock).
Покрывают: предобработку, Pydantic-валидацию, `/health`, `/predict` (200/401/422).

---

## 7. Демонстрация на защите

### Запуск

```bash
# Windows (без Docker):
.venv\Scripts\activate
python run.py

# Или через Docker Compose:
docker compose up --build
```

### Сценарий 1 — Health-check

```bash
curl http://localhost:8000/health
```

Ответ:
```json
{"status": "ok", "model_version": "1.0.0", "model_loaded": true}
```

### Сценарий 2 — Клиент с высоким риском оттока

(tenure=1, Fiber optic, Month-to-month, Electronic check)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: password123" \
  -d "{\"gender\":\"Male\",\"SeniorCitizen\":1,\"Partner\":\"No\",\"Dependents\":\"No\",\"tenure\":1,\"PhoneService\":\"Yes\",\"MultipleLines\":\"Yes\",\"InternetService\":\"Fiber optic\",\"OnlineSecurity\":\"No\",\"OnlineBackup\":\"No\",\"DeviceProtection\":\"No\",\"TechSupport\":\"No\",\"StreamingTV\":\"Yes\",\"StreamingMovies\":\"Yes\",\"Contract\":\"Month-to-month\",\"PaperlessBilling\":\"Yes\",\"PaymentMethod\":\"Electronic check\",\"MonthlyCharges\":95.0,\"TotalCharges\":\"95.0\"}"
```

Ожидаемый ответ: `churn_prediction: 1`, `churn_probability > 0.70`

### Сценарий 3 — Клиент с низким риском оттока

(tenure=60, DSL, Two year, Bank transfer)

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: password123" \
  -d "{\"gender\":\"Female\",\"SeniorCitizen\":0,\"Partner\":\"Yes\",\"Dependents\":\"Yes\",\"tenure\":60,\"PhoneService\":\"Yes\",\"MultipleLines\":\"No\",\"InternetService\":\"DSL\",\"OnlineSecurity\":\"Yes\",\"OnlineBackup\":\"Yes\",\"DeviceProtection\":\"Yes\",\"TechSupport\":\"Yes\",\"StreamingTV\":\"No\",\"StreamingMovies\":\"No\",\"Contract\":\"Two year\",\"PaperlessBilling\":\"No\",\"PaymentMethod\":\"Bank transfer (automatic)\",\"MonthlyCharges\":55.0,\"TotalCharges\":\"3300.0\"}"
```

Ожидаемый ответ: `churn_prediction: 0`, `churn_probability < 0.20`



---

## 8. Ограничения и дальнейшая работа

**Текущие ограничения:**
- Модель статична, нет дообучения на новых данных
- Нет мониторинга дрейфа данных
- Авторизация только по API-ключу 

**Что можно улучшить:**
- MLflow для трекинга экспериментов и версионирования моделей
- Optuna для байесовского поиска гиперпараметров
- Prometheus + Grafana для мониторинга производительности
- SHAP для объяснения конкретных предсказаний

---

## 9. Оценка проекта

Самооценка по 10 критериям — в `self-checklist.md`.
Подробное обоснование каждого пункта — там же.
