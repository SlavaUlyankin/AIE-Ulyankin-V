"""
tests/test_predictor.py

Тесты для проверки корректности кода.

Зачем нужны тесты:
  - Гарантируют, что после клонирования и установки зависимостей всё работает
  - Ловят регрессии при изменении кода
  - Чеклист 1: сервис должен работать по инструкции (тесты это проверяют)

Что тестируем:
  1. Preprocessing: логика предобработки без модели
  2. Schemas: Pydantic-валидация входных данных
  3. API smoke-тесты: /health и /predict через TestClient (модель замокана)

Запуск:
    pytest tests/ -v
"""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Фикстуры
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_customer() -> dict:
    """Пример данных клиента — тот же формат, что принимает /predict."""
    return {
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


@pytest.fixture
def high_risk_customer() -> dict:
    """Клиент с высоким риском оттока: Month-to-month, Fiber optic, tenure=1."""
    return {
        "gender": "Male",
        "SeniorCitizen": 1,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 1,
        "PhoneService": "Yes",
        "MultipleLines": "Yes",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "No",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 95.0,
        "TotalCharges": "95.0",
    }


@pytest.fixture
def mock_predictor():
    """
    Мок ChurnPredictor — позволяет тестировать API без реальных файлов модели.
    Зачем: артефакты (model.pkl) создаются в ноутбуках и не хранятся в git.
    """
    predictor = MagicMock()
    predictor.is_loaded.return_value = True
    predictor.version = "1.0.0"
    predictor.predict.return_value = {
        "churn_probability": 0.73,
        "churn_prediction": 1,
        "model_version": "1.0.0",
    }
    return predictor


@pytest.fixture
def client(mock_predictor):
    """
    TestClient с замоканным предиктором.
    patch заменяет реальную загрузку модели на наш мок при старте приложения.
    """
    # Патчим ChurnPredictor до импорта main, чтобы lifespan не упал
    with patch("src.service.main.ChurnPredictor") as MockClass:
        MockClass.return_value = mock_predictor

        from src.service.main import app
        with TestClient(app, raise_server_exceptions=True) as c:
            # Вручную кладём предиктор в app.state (lifespan уже выполнился)
            app.state.predictor = mock_predictor
            yield c


# ─────────────────────────────────────────────────────────────────────────────
# 1. Тесты предобработки (без модели)
# ─────────────────────────────────────────────────────────────────────────────

class TestPreprocessor:
    """Проверяем логику предобработки данных."""

    def test_total_charges_converted_to_float(self, sample_customer):
        """TotalCharges должна конвертироваться в float корректно."""
        tc_val = float(sample_customer["TotalCharges"])
        assert isinstance(tc_val, float)
        assert tc_val == 786.0

    def test_sample_has_all_required_fields(self, sample_customer):
        """Все 19 обязательных полей присутствуют в тестовом примере."""
        required_fields = [
            "gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
            "PhoneService", "MultipleLines", "InternetService",
            "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
            "StreamingTV", "StreamingMovies", "Contract", "PaperlessBilling",
            "PaymentMethod", "MonthlyCharges", "TotalCharges",
        ]
        for field in required_fields:
            assert field in sample_customer, f"Missing required field: {field}"

    def test_preprocess_single_returns_dataframe(self, sample_customer):
        """preprocess_single возвращает DataFrame с правильными типами."""
        from sklearn.preprocessing import LabelEncoder
        import numpy as np

        # Минимальный набор энкодеров для теста
        cat_cols = [
            "gender", "Partner", "Dependents", "PhoneService",
            "MultipleLines", "InternetService", "OnlineSecurity",
            "OnlineBackup", "DeviceProtection", "TechSupport",
            "StreamingTV", "StreamingMovies", "Contract",
            "PaperlessBilling", "PaymentMethod",
        ]
        encoders = {"TotalCharges_median": 1397.475}
        for col in cat_cols:
            le = LabelEncoder()
            le.fit([sample_customer[col], "dummy_other"])
            encoders[col] = le

        from src.data.preprocessor import preprocess_single
        result = preprocess_single(sample_customer, encoders)

        assert isinstance(result, pd.DataFrame), "preprocess_single must return DataFrame"
        assert result.shape[0] == 1, "Must return exactly 1 row"
        assert result.shape[1] > 0, "Must have at least 1 column"

    def test_preprocessor_class_exists(self):
        """Класс Preprocessor импортируется без ошибок."""
        from src.data.preprocessor import Preprocessor
        prep = Preprocessor()
        assert not prep._fitted, "New preprocessor should not be fitted"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Тесты Pydantic-валидации
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemas:
    """Проверяем валидацию входных данных."""

    def test_valid_customer_accepted(self, sample_customer):
        """Корректные данные должны приниматься без ошибок."""
        from src.service.schemas import CustomerRequest
        customer = CustomerRequest(**sample_customer)
        assert customer.tenure == 12
        assert customer.MonthlyCharges == 65.5

    def test_invalid_gender_rejected(self, sample_customer):
        """Недопустимое значение gender должно вызывать ValidationError."""
        from pydantic import ValidationError
        from src.service.schemas import CustomerRequest
        sample_customer["gender"] = "Unknown"
        with pytest.raises(ValidationError):
            CustomerRequest(**sample_customer)

    def test_invalid_contract_rejected(self, sample_customer):
        """Недопустимое значение Contract должно вызывать ValidationError."""
        from pydantic import ValidationError
        from src.service.schemas import CustomerRequest
        sample_customer["Contract"] = "Weekly"
        with pytest.raises(ValidationError):
            CustomerRequest(**sample_customer)

    def test_invalid_total_charges_rejected(self, sample_customer):
        """Нечисловой TotalCharges должен вызывать ValidationError."""
        from pydantic import ValidationError
        from src.service.schemas import CustomerRequest
        sample_customer["TotalCharges"] = "not_a_number"
        with pytest.raises(ValidationError):
            CustomerRequest(**sample_customer)

    def test_senior_citizen_out_of_range(self, sample_customer):
        """SeniorCitizen не может быть больше 1."""
        from pydantic import ValidationError
        from src.service.schemas import CustomerRequest
        sample_customer["SeniorCitizen"] = 5
        with pytest.raises(ValidationError):
            CustomerRequest(**sample_customer)

    def test_health_response_schema(self):
        """HealthResponse принимает корректные данные."""
        from src.service.schemas import HealthResponse
        resp = HealthResponse(status="ok", model_version="1.0.0", model_loaded=True)
        assert resp.status == "ok"
        assert resp.model_loaded is True


# ─────────────────────────────────────────────────────────────────────────────
# 3. Smoke-тесты API (через TestClient, модель замокана)
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Тесты /health — не требует API-ключа."""

    def test_health_returns_200(self, client):
        """GET /health должен возвращать 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """Ответ /health должен содержать status, model_version, model_loaded."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "model_version" in data
        assert "model_loaded" in data
        assert data["model_loaded"] is True

    def test_health_model_version(self, client):
        """/health возвращает версию модели из predictor.version."""
        response = client.get("/health")
        data = response.json()
        assert data["model_version"] == "1.0.0"


class TestPredictEndpoint:
    """Тесты /predict."""

    API_KEY = "test_key"

    @pytest.fixture(autouse=True)
    def patch_api_key(self, monkeypatch):
        """Устанавливаем тестовый API-ключ через monkeypatch."""
        monkeypatch.setenv("API_KEY", self.API_KEY)
        # Обновляем settings напрямую
        from src.config import settings
        settings.API_KEY = self.API_KEY

    def test_predict_requires_api_key(self, client, sample_customer):
        """Запрос без X-API-Key должен вернуть 401."""
        response = client.post("/predict", json=sample_customer)
        assert response.status_code == 401

    def test_predict_with_valid_key_returns_200(self, client, sample_customer):
        """Запрос с верным ключом и корректными данными → 200."""
        response = client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        assert response.status_code == 200

    def test_predict_response_has_required_fields(self, client, sample_customer):
        """Ответ /predict содержит churn_probability, churn_prediction, model_version."""
        response = client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        data = response.json()
        assert "churn_probability" in data
        assert "churn_prediction" in data
        assert "model_version" in data

    def test_predict_probability_in_range(self, client, sample_customer):
        """churn_probability должна быть в диапазоне [0, 1]."""
        response = client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        prob = response.json()["churn_probability"]
        assert 0.0 <= prob <= 1.0, f"Probability out of range: {prob}"

    def test_predict_label_is_binary(self, client, sample_customer):
        """churn_prediction должен быть 0 или 1."""
        response = client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        label = response.json()["churn_prediction"]
        assert label in (0, 1), f"Label must be 0 or 1, got {label}"

    def test_predict_invalid_data_returns_422(self, client, sample_customer):
        """Невалидные данные (неверный gender) → 422 Unprocessable Entity."""
        sample_customer["gender"] = "INVALID"
        response = client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        assert response.status_code == 422

    def test_predict_missing_field_returns_422(self, client, sample_customer):
        """Отсутствие обязательного поля → 422."""
        del sample_customer["Contract"]
        response = client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        assert response.status_code == 422

    def test_predict_called_with_correct_data(self, client, sample_customer, mock_predictor):
        """predictor.predict() вызывается с правильными данными клиента."""
        client.post(
            "/predict",
            json=sample_customer,
            headers={"X-API-Key": self.API_KEY},
        )
        mock_predictor.predict.assert_called_once()
        call_args = mock_predictor.predict.call_args[0][0]
        assert call_args["gender"] == "Female"
        assert call_args["Contract"] == "Month-to-month"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Тест конфигурации (чеклист 7)
# ─────────────────────────────────────────────────────────────────────────────

class TestConfig:
    """Проверяем, что конфиг читается из переменных окружения."""

    def test_config_imports_without_error(self):
        """src/config.py импортируется без ошибок."""
        from src.config import settings
        assert settings is not None

    def test_config_has_required_keys(self):
        """Все обязательные поля конфига присутствуют."""
        from src.config import settings
        assert hasattr(settings, "MODEL_PATH")
        assert hasattr(settings, "PREPROCESSOR_PATH")
        assert hasattr(settings, "API_KEY")
        assert hasattr(settings, "LOG_LEVEL")
        assert hasattr(settings, "PORT")

    def test_model_path_is_string(self):
        """MODEL_PATH должен быть строкой (не None)."""
        from src.config import settings
        assert isinstance(settings.MODEL_PATH, str)
        assert len(settings.MODEL_PATH) > 0
