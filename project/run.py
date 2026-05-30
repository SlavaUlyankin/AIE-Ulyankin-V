"""
run.py

Точка входа для запуска сервиса без Docker.
Читает HOST и PORT из .env через src/config.py.

Использование:
    python run.py
    # или
    uvicorn src.service.main:app --host 0.0.0.0 --port 8000 --reload
"""

import uvicorn
from src.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.service.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
