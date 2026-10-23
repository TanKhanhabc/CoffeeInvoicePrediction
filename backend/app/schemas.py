from pydantic import BaseModel, Field
from enum import Enum

# Khai báo Enum cho các ca làm
class ShiftEnum(str, Enum):
    night = "Night"
    morning = "Morning"
    afternoon = "Afternoon"
    evening = "Evening"

class PredictionRequest(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format", json_schema_extra={"example": "2023-11-20"})
    shift: ShiftEnum = Field(..., description="Night, Morning, Afternoon, or Evening")
    is_holiday: bool = Field(default=False, description="Is holiday flag")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2023-11-20",
                "shift": "Morning",
                "is_holiday": False
            }
        }

class PredictionResponse(BaseModel):
    date: str
    shift: str
    is_holiday: bool
    predicted_invoice_count: int
    unit: str = "invoices"
    model: str = "RandomForestRegressor baseline"