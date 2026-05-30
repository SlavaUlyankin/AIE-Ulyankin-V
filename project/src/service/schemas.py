"""
src/service/schemas.py

Типизированные Pydantic-модели для запроса и ответа /predict.

Чеклист:
  - пункт 2: валидация входных данных до инференса
  - пункт 5: структура в src/
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Допустимые значения для категориальных признаков ─────────────────────────

GENDER_VALUES         = {"Male", "Female"}
YES_NO                = {"Yes", "No"}
YES_NO_NO_PHONE       = {"Yes", "No", "No phone service"}
YES_NO_NO_INTERNET    = {"Yes", "No", "No internet service"}
INTERNET_SERVICE      = {"DSL", "Fiber optic", "No"}
CONTRACT_VALUES       = {"Month-to-month", "One year", "Two year"}
PAYMENT_METHODS       = {
    "Electronic check",
    "Mailed check",
    "Bank transfer (automatic)",
    "Credit card (automatic)",
}


class CustomerRequest(BaseModel):
    """
    Данные клиента для предсказания оттока.
    Соответствует схеме датасета IBM Telco Customer Churn.
    """

    gender:           str   = Field(..., description="Male или Female")
    SeniorCitizen:    int   = Field(..., ge=0, le=1, description="1 = пенсионер")
    Partner:          str   = Field(..., description="Yes/No — есть ли партнёр")
    Dependents:       str   = Field(..., description="Yes/No — есть ли иждивенцы")
    tenure:           int   = Field(..., ge=0, le=72, description="Стаж клиента в месяцах")
    PhoneService:     str   = Field(..., description="Yes/No — телефонная линия")
    MultipleLines:    str   = Field(..., description="Yes / No / No phone service")
    InternetService:  str   = Field(..., description="DSL / Fiber optic / No")
    OnlineSecurity:   str   = Field(..., description="Yes / No / No internet service")
    OnlineBackup:     str   = Field(..., description="Yes / No / No internet service")
    DeviceProtection: str   = Field(..., description="Yes / No / No internet service")
    TechSupport:      str   = Field(..., description="Yes / No / No internet service")
    StreamingTV:      str   = Field(..., description="Yes / No / No internet service")
    StreamingMovies:  str   = Field(..., description="Yes / No / No internet service")
    Contract:         str   = Field(..., description="Month-to-month / One year / Two year")
    PaperlessBilling: str   = Field(..., description="Yes/No — электронный счёт")
    PaymentMethod:    str   = Field(..., description="Способ оплаты")
    MonthlyCharges:   float = Field(..., ge=0, description="Ежемесячный платёж, $")
    TotalCharges:     str   = Field(..., description="Суммарные платежи (строка, как в датасете)")

    # ── Валидаторы ────────────────────────────────────────────────────────────

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        if v not in GENDER_VALUES:
            raise ValueError(f"gender must be one of {GENDER_VALUES}, got '{v}'")
        return v

    @field_validator("Partner", "Dependents", "PhoneService", "PaperlessBilling")
    @classmethod
    def validate_yes_no(cls, v: str) -> str:
        if v not in YES_NO:
            raise ValueError(f"Value must be 'Yes' or 'No', got '{v}'")
        return v

    @field_validator("MultipleLines")
    @classmethod
    def validate_multiple_lines(cls, v: str) -> str:
        if v not in YES_NO_NO_PHONE:
            raise ValueError(f"MultipleLines must be one of {YES_NO_NO_PHONE}, got '{v}'")
        return v

    @field_validator("OnlineSecurity", "OnlineBackup", "DeviceProtection",
                     "TechSupport", "StreamingTV", "StreamingMovies")
    @classmethod
    def validate_internet_feature(cls, v: str) -> str:
        if v not in YES_NO_NO_INTERNET:
            raise ValueError(f"Value must be one of {YES_NO_NO_INTERNET}, got '{v}'")
        return v

    @field_validator("InternetService")
    @classmethod
    def validate_internet_service(cls, v: str) -> str:
        if v not in INTERNET_SERVICE:
            raise ValueError(f"InternetService must be one of {INTERNET_SERVICE}, got '{v}'")
        return v

    @field_validator("Contract")
    @classmethod
    def validate_contract(cls, v: str) -> str:
        if v not in CONTRACT_VALUES:
            raise ValueError(f"Contract must be one of {CONTRACT_VALUES}, got '{v}'")
        return v

    @field_validator("PaymentMethod")
    @classmethod
    def validate_payment_method(cls, v: str) -> str:
        if v not in PAYMENT_METHODS:
            raise ValueError(f"PaymentMethod must be one of {PAYMENT_METHODS}, got '{v}'")
        return v

    @field_validator("TotalCharges")
    @classmethod
    def validate_total_charges(cls, v: str) -> str:
        try:
            float(v)
        except ValueError:
            raise ValueError(f"TotalCharges must be a numeric string, got '{v}'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 12,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": "DSL",
                "OnlineSecurity": "No",
                "OnlineBackup": "Yes",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "No",
                "StreamingMovies": "No",
                "Contract": "Month-to-month",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 65.5,
                "TotalCharges": "786.0",
            }
        }
    }


class PredictionResponse(BaseModel):
    """Ответ эндпоинта /predict."""

    churn_probability: float = Field(..., description="Вероятность оттока [0, 1]")
    churn_prediction:  int   = Field(..., description="Метка класса: 0 = остаётся, 1 = уходит")
    model_version:     str   = Field(..., description="Версия модели")


class HealthResponse(BaseModel):
    """Ответ эндпоинта /health."""

    status:        Literal["ok"] = "ok"
    model_version: str
    model_loaded:  bool
