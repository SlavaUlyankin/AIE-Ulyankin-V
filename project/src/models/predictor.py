"""
src/models/predictor.py

Загрузка обученной модели и инференс.

Чеклист:
  - пункт 2: /predict вызывает реальную модель (не заглушку)
  - пункт 5: структурированный код в src/
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ChurnPredictor:
    """
    Загружает обученную модель и препроцессор, выполняет инференс.

    Использование в сервисе:
        predictor = ChurnPredictor(
            model_path="artifacts/model.pkl",
            encoders_path="artifacts/encoders.pkl",
        )
        result = predictor.predict(customer_data_dict)
    """

    def __init__(
        self,
        model_path: str | Path,
        encoders_path: str | Path,
        meta_path: Optional[str | Path] = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.encoders_path = Path(encoders_path)
        self.meta_path = Path(meta_path) if meta_path else None

        self._model = None
        self._encoders: dict = {}
        self._meta: dict = {}
        self._version: str = "unknown"

        self._load()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Загружает модель и препроцессор с диска."""
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}\n"
                "Run notebooks/02_models.ipynb first to train and save the model."
            )
        if not self.encoders_path.exists():
            raise FileNotFoundError(
                f"Encoders file not found: {self.encoders_path}\n"
                "Run notebooks/01_eda.ipynb first to save the encoders."
            )

        self._model = joblib.load(self.model_path)
        self._encoders = joblib.load(self.encoders_path)
        logger.info("Model loaded from %s", self.model_path)
        logger.info("Encoders loaded from %s", self.encoders_path)

        # Метаданные (версия, метрики) — опционально
        if self.meta_path and self.meta_path.exists():
            with open(self.meta_path, encoding="utf-8") as f:
                self._meta = json.load(f)
            self._version = self._meta.get("version", "1.0.0")
            logger.info("Model version: %s", self._version)
        else:
            self._version = "1.0.0"

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, record: dict) -> dict:
        """
        Предсказание для одного клиента.

        Args:
            record: словарь с полями клиента (без customerID и Churn)

        Returns:
            {
              "churn_probability": float,   # вероятность оттока [0, 1]
              "churn_prediction": int,       # 0 или 1
              "model_version": str
            }
        """
        from src.data.preprocessor import preprocess_single  # локальный импорт для избегания цикла

        X = preprocess_single(record, self._encoders)
        proba = float(self._model.predict_proba(X)[0, 1])
        prediction = int(proba >= 0.5)

        logger.debug(
            "Prediction: probability=%.4f, label=%d", proba, prediction
        )

        return {
            "churn_probability": round(proba, 4),
            "churn_prediction": prediction,
            "model_version": self._version,
        }

    def predict_batch(self, records: list[dict]) -> list[dict]:
        """
        Пакетное предсказание для списка клиентов.

        Args:
            records: список словарей с данными клиентов

        Returns:
            список результатов predict()
        """
        return [self.predict(r) for r in records]

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def version(self) -> str:
        return self._version

    @property
    def meta(self) -> dict:
        return self._meta

    def is_loaded(self) -> bool:
        return self._model is not None
