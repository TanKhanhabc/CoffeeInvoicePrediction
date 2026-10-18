from datetime import date
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split
from app.services.data_service import aggregate_invoice_counts, load_enriched_data

SHIFTS = ["Night", "Morning", "Afternoon", "Evening"]
SHIFT_TO_CODE = {name: idx for idx, name in enumerate(SHIFTS)}

def feature_frame(df):
    result = df.copy()
    result["shift_code"] = result["shift"].map(SHIFT_TO_CODE).fillna(0).astype(int)
    return result[["day_of_week", "month", "shift_code", "is_holiday"]].astype(float)

def build_training_data():
    raw = load_enriched_data()
    grouped = aggregate_invoice_counts(raw)
    grouped["date_dt"] = grouped["date"].map(date.fromisoformat)
    grouped["day_of_week"] = grouped["date_dt"].map(lambda d: d.weekday())
    grouped["month"] = grouped["date_dt"].map(lambda d: d.month)
    return grouped

def train_baseline():
    grouped = build_training_data()
    X = feature_frame(grouped)
    y = grouped["invoice_count"]
    model = RandomForestRegressor(n_estimators=200, random_state=42, min_samples_leaf=2)
    # Starter fit uses all available history. Evaluation should be added with chronological holdout.
    model.fit(X, y)
    return model, grouped

def predict_count(target_date: str, shift: str, is_holiday: bool) -> int:
    if shift not in SHIFTS:
        raise ValueError(f"shift must be one of: {', '.join(SHIFTS)}")
    parsed = date.fromisoformat(target_date)
    import pandas as pd
    row = pd.DataFrame([{
        "day_of_week": parsed.weekday(),
        "month": parsed.month,
        "shift": shift,
        "is_holiday": bool(is_holiday),
    }])
    model, _ = train_baseline()
    prediction = float(model.predict(feature_frame(row))[0])
    return max(0, int(round(prediction)))
