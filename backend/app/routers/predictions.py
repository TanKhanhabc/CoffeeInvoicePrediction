from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.ml.model_service import predict_count

router = APIRouter(prefix="/api", tags=["prediction"])

class PredictionRequest(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    shift: str = Field(..., description="Night, Morning, Afternoon, or Evening")
    is_holiday: bool = False

@router.post("/predict")
def predict(request: PredictionRequest):
    try:
        count = predict_count(request.date, request.shift, request.is_holiday)
        return {
            "date": request.date,
            "shift": request.shift,
            "is_holiday": request.is_holiday,
            "predicted_invoice_count": count,
            "unit": "invoices",
            "model": "RandomForestRegressor baseline",
        }
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
