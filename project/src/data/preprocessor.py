"""
src/data/preprocessor.py

Пайплайн предобработки данных.
Логика идентична notebooks/01_eda.ipynb — принцип DRY.

Чеклист:
  - пункт 3: предобработка данных
  - пункт 5: структурированный код в src/
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# Порядок признаков, на котором обучена модель (фиксируем явно)
FEATURE_ORDER = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
    "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
    "StreamingTV", "StreamingMovies", "Contract", "PaperlessBilling",
    "PaymentMethod", "MonthlyCharges", "TotalCharges",
]


class Preprocessor:
    """
    Предобрабатывает сырые данные клиента для инференса.

    Использование:
        # Обучение (в ноутбуке / train-скрипте):
        prep = Preprocessor()
        X_train, y_train = prep.fit_transform(train_df)
        prep.save("artifacts/preprocessor.pkl")

        # Инференс (в сервисе):
        prep = Preprocessor.load("artifacts/preprocessor.pkl")
        X = prep.transform(input_df)
    """

    def __init__(self) -> None:
        self.encoders: dict = {}
        self._fitted: bool = False

    # ── Public API ────────────────────────────────────────────────────────────

    def fit_transform(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, Optional[pd.Series]]:
        """Обучает энкодеры и трансформирует данные (только для train)."""
        result, y, self.encoders = _preprocess_core(df, fit=True, encoders=None)
        self._fitted = True
        logger.info("Preprocessor fitted. Features: %d", result.shape[1])
        return result, y

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Трансформирует данные без переобучения (для val/test/инференса)."""
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted. Call fit_transform() or load().")
        result, _, _ = _preprocess_core(df, fit=False, encoders=self.encoders)
        return result

    def save(self, path: str | Path) -> None:
        """Сериализует препроцессор в файл."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"encoders": self.encoders, "fitted": self._fitted}, path)
        logger.info("Preprocessor saved to %s", path)

    @classmethod
    def load(cls, path: str | Path) -> "Preprocessor":
        """Загружает препроцессор из файла."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Preprocessor file not found: {path}")
        data = joblib.load(path)
        prep = cls()
        prep.encoders = data["encoders"]
        prep._fitted = data["fitted"]
        logger.info("Preprocessor loaded from %s", path)
        return prep


# ── Core logic (зеркалит notebook) ───────────────────────────────────────────

def _preprocess_core(
    df: pd.DataFrame,
    fit: bool,
    encoders: Optional[dict],
) -> tuple[pd.DataFrame, Optional[pd.Series], dict]:
    """
    Внутренняя функция предобработки.
    Идентична логике в notebooks/01_eda.ipynb.

    Args:
        df:       исходный DataFrame
        fit:      True — обучать энкодеры (только train)
        encoders: словарь обученных энкодеров (для val/test)

    Returns:
        (X, y, encoders)
    """
    df = df.copy()
    if encoders is None:
        encoders = {}

    # ── Шаг 1: Удалить customerID ────────────────────────────────────────────
    df.drop(columns=["customerID"], inplace=True, errors="ignore")

    # ── Шаг 2: TotalCharges → float ──────────────────────────────────────────
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    if fit:
        encoders["TotalCharges_median"] = df["TotalCharges"].median()
    df["TotalCharges"] = df["TotalCharges"].fillna(encoders["TotalCharges_median"])

    # ── Шаг 3: Целевая переменная ────────────────────────────────────────────
    y: Optional[pd.Series] = None
    if "Churn" in df.columns:
        y = (df["Churn"] == "Yes").astype(int)
        df.drop(columns=["Churn"], inplace=True)

    # ── Шаг 4: LabelEncoder для категориальных признаков ─────────────────────
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    if fit:
        for col in cat_cols:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
    else:
        for col in cat_cols:
            if col not in encoders:
                raise KeyError(f"No encoder found for column '{col}'")
            le: LabelEncoder = encoders[col]
            known = set(le.classes_)
            # Unseen labels → первый известный класс
            df[col] = df[col].astype(str).apply(
                lambda x: x if x in known else le.classes_[0]
            )
            df[col] = le.transform(df[col])

    # ── Шаг 5: Зафиксировать порядок признаков ───────────────────────────────
    available = [c for c in FEATURE_ORDER if c in df.columns]
    df = df[available]

    return df, y, encoders


def preprocess_single(record: dict, encoders: dict) -> pd.DataFrame:
    """
    Удобная функция для инференса одной записи (из API-запроса).

    Args:
        record:   словарь с полями клиента (без customerID и Churn)
        encoders: словарь обученных энкодеров

    Returns:
        DataFrame с одной строкой, готовый для model.predict()
    """
    df = pd.DataFrame([record])
    result, _, _ = _preprocess_core(df, fit=False, encoders=encoders)
    return result
