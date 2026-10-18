from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW_PATH = ROOT / "data" / "raw" / "coffee_shop_sales.csv"
PROCESSED_PATH = ROOT / "data" / "processed" / "coffee_shop_sales_enriched.csv"

SHIFT_ORDER = ["Night", "Morning", "Afternoon", "Evening"]

def shift_from_hour(hour: int) -> str:
    if 0 <= hour <= 5:
        return "Night"
    if 6 <= hour <= 11:
        return "Morning"
    if 12 <= hour <= 16:
        return "Afternoon"
    return "Evening"

def load_enriched_data() -> pd.DataFrame:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {RAW_PATH}")
    df = pd.read_csv(RAW_PATH)
    if "timestamp" not in df.columns:
        raise ValueError("Dataset must contain a 'timestamp' column.")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["timestamp"].dt.hour
    df["shift"] = df["hour"].apply(shift_from_hour)
    holiday_name = df["holiday_name"] if "holiday_name" in df.columns else pd.Series("", index=df.index)
    df["is_holiday"] = holiday_name.fillna("").astype(str).str.strip().ne("")
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_PATH, index=False)
    return df

def aggregate_invoice_counts(df: pd.DataFrame) -> pd.DataFrame:
    # Starter assumption: one CSV row/transaction_id is one invoice.
    return (df.groupby(["date", "shift", "is_holiday"], as_index=False)
              .agg(invoice_count=("transaction_id", "nunique"),
                   day_of_week=("day_of_week", "first"),
                   month=("month", "first"))
              .sort_values(["date", "shift"])
              .reset_index(drop=True))

def get_data_profile(df: pd.DataFrame) -> dict:
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "column_names": list(df.columns),
        "missing_values": {str(k): int(v) for k, v in df.isna().sum().items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "holiday_rows": int(df["is_holiday"].sum()),
        "shift_counts": {str(k): int(v) for k, v in df["shift"].value_counts().items()},
    }
