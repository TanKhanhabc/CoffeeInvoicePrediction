from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from enum import Enum

router = APIRouter(prefix="/api", tags=["prediction"])

try:
    from app.ml.model_service import predict_count
    HAS_MODEL = True
except ImportError:
    HAS_MODEL = False


class ShiftEnum(str, Enum):
    night = "Night"
    morning = "Morning"
    afternoon = "Afternoon"
    evening = "Evening"


class PredictionRequest(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format", example="2023-11-20")
    shift: ShiftEnum = Field(..., description="Night, Morning, Afternoon, or Evening")
    is_holiday: bool = Field(default=False, description="Is holiday flag")


@router.post("/predict")
def predict(request: PredictionRequest):
    shift_val = request.shift.value if isinstance(request.shift, Enum) else request.shift
    
    if HAS_MODEL:
        try:
            count = predict_count(request.date, shift_val, request.is_holiday)
            return {
                "date": request.date,
                "shift": shift_val,
                "is_holiday": request.is_holiday,
                "predicted_invoice_count": count,
                "unit": "invoices",
                "model": "RandomForestRegressor baseline",
            }
        except (ValueError, TypeError) as exc:
            # Lỗi dữ liệu đầu vào sai từ phía người dùng
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception:
            # Nếu model_service bị lỗi hệ thống (thiếu file pkl, v.v.), fallback về Stub
            pass

    # 2. Fallback Mock Stub: Trả số mẫu khi model thật chưa tải/sẵn sàng
    return {
        "date": request.date,
        "shift": shift_val,
        "is_holiday": request.is_holiday,
        "predicted_invoice_count": 12,
        "unit": "invoices",
        "model": "RandomForestRegressor baseline (Mock Stub)",
    }