"""
src/service/main.py

FastAPI-приложение: /health, /predict, логирование, безопасность, обработка ошибок.

Чеклист:
  - пункт 1: сервис запускается по инструкции из README.md
  - пункт 2: /predict вызывает реальную модель (не заглушку)
  - пункт 7: API_KEY читается из .env, не хардкодится
  - пункт 8: логи через logging, endpoint /health
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

from src.config import settings
from src.models.predictor import ChurnPredictor
from src.service.logger import setup_logging
from src.service.schemas import CustomerRequest, HealthResponse, PredictionResponse

# ── Логирование инициализируется первым ───────────────────────────────────────
setup_logging(level=settings.LOG_LEVEL, log_file=settings.LOG_FILE)
logger = logging.getLogger(__name__)


# ── Жизненный цикл приложения (lifespan) ─────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Загружает модель при старте, освобождает ресурсы при остановке.
    Современная замена устаревшим @app.on_event("startup").
    """
    logger.info("Starting up Churn Prediction Service...")
    logger.info("MODEL_PATH=%s", settings.MODEL_PATH)
    logger.info("LOG_LEVEL=%s", settings.LOG_LEVEL)

    try:
        predictor = ChurnPredictor(
            model_path=settings.MODEL_PATH,
            encoders_path=settings.PREPROCESSOR_PATH,
            meta_path=settings.MODEL_META_PATH,
        )
        app.state.predictor = predictor
        logger.info(
            "Model loaded successfully. Version=%s", predictor.version
        )
    except FileNotFoundError as exc:
        logger.critical("STARTUP FAILED: %s", exc)
        raise RuntimeError(str(exc)) from exc

    yield  # ← сервис работает

    logger.info("Shutting down Churn Prediction Service.")


# ── Приложение ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Churn Prediction API",
    description=(
        "Предсказание оттока клиентов телеком-оператора. "
        "Используется CatBoostClassifier, обученный на IBM Telco Customer Churn."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── Безопасность: API-ключ в заголовке ───────────────────────────────────────
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Dependency: проверяет X-API-Key из заголовка запроса.
    Ключ берётся из .env (переменная API_KEY) — чеклист 7.
    """
    if not api_key or api_key != settings.API_KEY:
        logger.warning("Unauthorized request: invalid or missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Pass it in 'X-API-Key' header.",
        )
    return api_key


# ── Обработчики ошибок ────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """422 Unprocessable Entity — невалидные входные данные.

    Pydantic v2 кладёт в exc.errors() объекты ValueError внутри поля 'ctx'.
    json.dumps не умеет их сериализовать → явно приводим всё к строкам.
    """
    # Безопасная сериализация: конвертируем любые не-JSON типы в строку
    safe_errors = []
    for err in exc.errors():
        safe_err = {
            "type":  err.get("type"),
            "loc":   [str(loc) for loc in err.get("loc", [])],
            "msg":   err.get("msg"),
            "input": str(err.get("input")),
        }
        safe_errors.append(safe_err)

    logger.warning(
        "Validation error on %s %s: %s",
        request.method, request.url.path, safe_errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": safe_errors,
            "hint": "Check field names and allowed values in /docs",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """500 Internal Server Error — неожиданные ошибки."""
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ── Middleware: логируем каждый запрос ────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирует метод, путь и время обработки каждого HTTP-запроса."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "%s %s → %d (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health-check",
    tags=["Observability"],
)
async def health_check(request: Request) -> HealthResponse:
    """
    Проверка работоспособности сервиса и наличия загруженной модели.
    Чеклист 8: endpoint /health.
    """
    predictor: ChurnPredictor = request.app.state.predictor
    return HealthResponse(
        status="ok",
        model_version=predictor.version,
        model_loaded=predictor.is_loaded(),
    )


@app.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Предсказание оттока клиента",
    tags=["Prediction"],
    dependencies=[Depends(verify_api_key)],
)
async def predict(
    request: Request,
    customer: CustomerRequest,
) -> PredictionResponse:
    """
    Принимает данные клиента, возвращает вероятность оттока.

    - Валидация входных данных — Pydantic (чеклист 2)
    - Препроцессинг — `src/data/preprocessor.py`
    - Инференс — реальная обученная CatBoost-модель (чеклист 2)
    - Логирование времени и результата (чеклист 8)
    """
    predictor: ChurnPredictor = request.app.state.predictor

    t_start = time.perf_counter()

    try:
        result = predictor.predict(customer.model_dump())
    except Exception as exc:
        logger.error("Prediction failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - t_start) * 1000

    # Логируем ключевые поля запроса и результат (чеклист 8)
    logger.info(
        "PREDICT | contract=%s tenure=%s monthly=%.1f | "
        "prob=%.4f label=%d | %.1f ms",
        customer.Contract,
        customer.tenure,
        customer.MonthlyCharges,
        result["churn_probability"],
        result["churn_prediction"],
        elapsed_ms,
    )

    return PredictionResponse(**result)
