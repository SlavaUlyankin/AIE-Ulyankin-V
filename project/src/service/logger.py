"""
src/service/logger.py

Настройка логирования: консоль + файл, формат с timestamp.

Чеклист:
  - пункт 8: логи через logging, уровень INFO, timestamp
"""

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str = "") -> None:
    """
    Инициализирует логирование для всего приложения.

    Args:
        level:    уровень логирования (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: путь к файлу лога (пустая строка = только консоль)
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Формат: время | уровень | модуль | сообщение
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)

    handlers: list[logging.Handler] = []

    # ── Консольный хендлер (всегда) ───────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    # ── Файловый хендлер (если задан LOG_FILE) ────────────────────────────────
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # ── Применяем настройки к корневому логгеру ───────────────────────────────
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True,  # переопределяем существующие хендлеры (важно для uvicorn)
    )

    # Подавляем слишком шумные библиотеки
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("catboost").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured: level=%s, file=%s",
        level,
        log_file or "stdout only",
    )
