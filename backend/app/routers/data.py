from fastapi import APIRouter
from app.services.data_service import load_enriched_data, get_data_profile

router = APIRouter(prefix="/api", tags=["data"])

@router.get("/data-profile")
def data_profile():
    return get_data_profile(load_enriched_data())

@router.get("/overview")
def overview():
    df = load_enriched_data()
    return {
        "transaction_rows": int(len(df)),
        "date_start": str(df["date"].min()),
        "date_end": str(df["date"].max()),
        "unique_stores": int(df["store_id"].nunique()) if "store_id" in df else 0,
        "holiday_rows": int(df["is_holiday"].sum()),
        "daily_shift_groups": int(df.groupby(["date", "shift"]).ngroups),
    }

@router.get("/history")
def history(limit: int = 30):
    df = load_enriched_data()
    grouped = (df.groupby(["date", "shift", "is_holiday"], as_index=False)
                 .agg(invoice_count=("transaction_id", "nunique"))
                 .sort_values(["date", "shift"], ascending=[False, True])
                 .head(max(1, min(limit, 500))))
    return grouped.to_dict(orient="records")
