from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    """Kiểm thử route /api/health"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_predict_success():
    """Kiểm thử route POST /api/predict với dữ liệu hợp lệ"""
    payload = {
        "date": "2023-11-20",
        "shift": "Morning",
        "is_holiday": False
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_invoice_count" in data
    assert data["shift"] == "Morning"
    assert isinstance(data["predicted_invoice_count"], int)

def test_predict_invalid_shift():
    """Kiểm thử validation route /api/predict khi gửi ca làm sai (Shift)"""
    payload = {
        "date": "2023-11-20",
        "shift": "Midday",  # Ca làm không hợp lệ
        "is_holiday": False
    }
    response = client.post("/api/predict", json=payload)
    # Phải trả về 422 Unprocessable Entity do Pydantic chặn
    assert response.status_code == 422

def test_overview():
    """Kiểm thử route GET /api/overview"""
    response = client.get("/api/overview")
    assert response.status_code == 200

def test_history():
    """Kiểm thử route GET /api/history"""
    response = client.get("/api/history?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_data_profile():
    """Kiểm thử route GET /api/data-profile"""
    response = client.get("/api/data-profile")
    assert response.status_code == 200