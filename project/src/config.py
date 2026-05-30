"""
src/config.py

Централизованная конфигурация сервиса.
Читает переменные из .env (через pydantic-settings).

Чеклист:
  - пункт 7: секреты через .env.example, не хардкодятся в коде
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Все настройки сервиса берутся из переменных окружения или .env-файла.
    Значения по умолчанию используются только для локальной разработки.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ── Модель и артефакты ────────────────────────────────────────────────────
    MODEL_PATH: str = "artifacts/model.pkl"
    PREPROCESSOR_PATH: str = "artifacts/encoders.pkl"
    MODEL_META_PATH: str = "artifacts/model_meta.json"

    # ── Логирование ───────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # ── Сервер ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Безопасность ──────────────────────────────────────────────────────────
    API_KEY: str = "your_key_here"


# Единственный экземпляр настроек для всего приложения
settings = Settings()
