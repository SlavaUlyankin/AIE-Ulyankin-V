# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile
#
# Зачем нужен Docker:
#   - Сервис запускается одинаково на любой машине (твоей, преподавателя, сервере)
#   - Не нужно устанавливать Python и зависимости вручную
#   - Чеклист 6: есть Dockerfile и инструкция по запуску
#
# Структура:
#   Шаг 1 — базовый образ Python
#   Шаг 2 — зависимости (кешируются отдельным слоем — ускоряет пересборку)
#   Шаг 3 — копирование кода и артефактов
#   Шаг 4 — настройка окружения и запуск
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Мета-информация
LABEL maintainer="student" \
      description="Churn Prediction API — AIE course project" \
      version="1.0.0"

# Рабочая директория внутри контейнера
WORKDIR /app

# ── Шаг 1: Зависимости ───────────────────────────────────────────────────────
# Копируем ТОЛЬКО requirements.txt первым — Docker кеширует этот слой.
# Если ты изменишь код (но не requirements), пересборка пропустит pip install.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Шаг 2: Исходный код ──────────────────────────────────────────────────────
COPY src/   ./src/
COPY run.py .

# ── Шаг 3: Артефакты модели ──────────────────────────────────────────────────
# model.pkl и preprocessor.pkl должны быть созданы ДО сборки образа
# (запусти 01_eda.ipynb и 02_models.ipynb)
COPY artifacts/ ./artifacts/

# ── Шаг 4: Логи и окружение ──────────────────────────────────────────────────
RUN mkdir -p logs

# Переменные окружения по умолчанию (можно переопределить через --env-file)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    LOG_FILE=logs/app.log \
    MODEL_PATH=artifacts/model.pkl \
    PREPROCESSOR_PATH=artifacts/preprocessor.pkl \
    MODEL_META_PATH=artifacts/model_meta.json \
    API_KEY=your_key_here

# Открываем порт (документация для пользователя, не блокирует трафик сам по себе)
EXPOSE 8000

# ── Запуск сервиса ───────────────────────────────────────────────────────────
# Используем uvicorn напрямую — надёжнее чем через run.py в контейнере
CMD ["uvicorn", "src.service.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--log-level", "info"]
