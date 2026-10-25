"""Data service for the Coffee Invoice Forecast project (owner: Lê Trung Hưng).

Public interface (kept stable for the API and ML modules):
    load_enriched_data()            -> transaction-level DataFrame + date/shift/is_holiday
    aggregate_invoice_counts(df)    -> date + shift + is_holiday + invoice_count
    get_data_profile(df)            -> JSON-serialisable data-quality report

Run ``python -m app.services.data_service`` from ``backend/`` to regenerate the
files in ``data/processed/`` (enriched CSV, aggregated CSV, data_profile.json).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW_PATH = ROOT / "data" / "raw" / "coffee_shop_sales.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
PROCESSED_PATH = PROCESSED_DIR / "coffee_shop_sales_enriched.csv"
AGGREGATE_PATH = PROCESSED_DIR / "invoice_counts_by_date_shift.csv"
PROFILE_PATH = PROCESSED_DIR / "data_profile.json"

SHIFT_ORDER = ["Night", "Morning", "Afternoon", "Evening"]
REQUIRED_COLUMNS = ("transaction_id", "timestamp")
HOLIDAY_MODES = ("date", "row")


# --------------------------------------------------------------------------- #
# Derived fields
# --------------------------------------------------------------------------- #
def shift_from_hour(hour: int) -> str:
    """Night 00-05, Morning 06-11, Afternoon 12-16, Evening 17-23."""
    if not 0 <= hour <= 23:
        raise ValueError(f"hour must be between 0 and 23, got {hour}")
    if hour <= 5:
        return "Night"
    if hour <= 11:
        return "Morning"
    if hour <= 16:
        return "Afternoon"
    return "Evening"


def _shift_series(hours: pd.Series) -> pd.Series:
    """Vectorised version of shift_from_hour (same boundaries)."""
    shifts = pd.cut(hours, bins=[-1, 5, 11, 16, 23], labels=SHIFT_ORDER)
    return shifts.astype(object)


def _holiday_flag(df: pd.DataFrame) -> pd.Series:
    """True when holiday_name has content (blank / NaN -> False)."""
    if "holiday_name" not in df.columns:
        return pd.Series(False, index=df.index)
    names = df["holiday_name"].fillna("").astype(str).str.strip()
    return names.ne("")


def enrich(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamps and add date, hour, shift, is_holiday, is_holiday_date, day_of_week, month.

    Rows whose timestamp cannot be parsed are dropped, but the number is
    recorded in ``df.attrs`` and reported by ``get_data_profile``.
    ``is_holiday`` is row-level (holiday_name populated);
    ``is_holiday_date`` is True for every row of a date that has any holiday row.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"Dataset is missing required column(s): {missing}")

    timestamps = pd.to_datetime(raw["timestamp"], errors="coerce")
    invalid = int(timestamps.isna().sum())

    df = raw.loc[timestamps.notna()].copy()
    df["timestamp"] = timestamps.loc[timestamps.notna()]
    df["date"] = df["timestamp"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["timestamp"].dt.hour
    df["shift"] = _shift_series(df["hour"])
    df["is_holiday"] = _holiday_flag(df).astype(bool)
    df["is_holiday_date"] = df.groupby("date")["is_holiday"].transform("any").astype(bool)
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month

    df = df.reset_index(drop=True)
    df.attrs["raw_rows"] = int(len(raw))
    df.attrs["invalid_timestamp_rows"] = invalid
    return df


# --------------------------------------------------------------------------- #
# Loading (cached, side-effect free unless saving the default dataset)
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=4)
def _load_cached(path_str: str, mtime_ns: int) -> pd.DataFrame:
    # mtime_ns is part of the cache key so editing the CSV invalidates the cache.
    return enrich(pd.read_csv(path_str))


def _save_processed(df: pd.DataFrame, force: bool = False) -> None:
    """Write the enriched CSV if it is missing/outdated (or when forced)."""
    try:
        stale = (
            not PROCESSED_PATH.exists()
            or PROCESSED_PATH.stat().st_mtime < RAW_PATH.stat().st_mtime
        )
        if force or stale:
            PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(PROCESSED_PATH, index=False)
    except OSError:
        # A read-only disk must not break the API.
        pass


def load_enriched_data(path: Path | str | None = None, save: bool = True) -> pd.DataFrame:
    """Load the transaction CSV and add the derived columns.

    ``path``: CSV to read (default: data/raw/coffee_shop_sales.csv).
    ``save``: only applies to the default dataset; the enriched CSV in
    data/processed/ is (re)written only when it is missing or older than the raw file.
    Returns a copy, so callers may modify it freely.
    """
    raw_path = Path(path) if path is not None else RAW_PATH
    if not raw_path.exists():
        raise FileNotFoundError(f"Dataset not found: {raw_path}")
    df = _load_cached(str(raw_path), raw_path.stat().st_mtime_ns).copy()
    if save and path is None:
        _save_processed(df)
    return df


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #
def aggregate_invoice_counts(
    df: pd.DataFrame, holiday_mode: str = "date", fill_missing: bool = True
) -> pd.DataFrame:
    """Count unique transaction_id per date + shift (+ is_holiday).

    holiday_mode="date" (default): ``is_holiday`` is True when ANY row of that date is a
        holiday, so there is exactly one row per date + shift. This avoids splitting a
        date into two partial groups when only some countries celebrate a holiday.
    holiday_mode="row": literal grouping by the row-level is_holiday flag.
    fill_missing (date mode only): add invoice_count = 0 for shifts without
        transactions so every calendar day has all 4 shifts.

    Columns: date (YYYY-MM-DD str), shift, is_holiday (bool), invoice_count (int),
    day_of_week, month.
    """
    if holiday_mode not in HOLIDAY_MODES:
        raise ValueError(f"holiday_mode must be one of {HOLIDAY_MODES}")
    needed = {"date", "shift", "is_holiday", "transaction_id"}
    absent = needed.difference(df.columns)
    if absent:
        raise ValueError(f"Missing columns for aggregation: {sorted(absent)}")

    columns = ["date", "shift", "is_holiday", "invoice_count", "day_of_week", "month"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    if holiday_mode == "date":
        day_flag = df.groupby("date")["is_holiday"].any()
        counts = df.groupby(["date", "shift"])["transaction_id"].nunique()
        if fill_missing:
            days = pd.date_range(pd.to_datetime(df["date"].min()),
                                 pd.to_datetime(df["date"].max()), freq="D")
            index = pd.MultiIndex.from_product(
                [days.strftime("%Y-%m-%d"), SHIFT_ORDER], names=["date", "shift"]
            )
            counts = counts.reindex(index, fill_value=0)
        out = counts.rename("invoice_count").reset_index()
        out["is_holiday"] = out["date"].isin(day_flag[day_flag].index)
    else:
        out = (df.groupby(["date", "shift", "is_holiday"], as_index=False)
                 .agg(invoice_count=("transaction_id", "nunique")))

    out["invoice_count"] = out["invoice_count"].astype(int)
    dates = pd.to_datetime(out["date"])
    out["day_of_week"] = dates.dt.dayofweek
    out["month"] = dates.dt.month
    order = out["shift"].map({name: i for i, name in enumerate(SHIFT_ORDER)})
    out = (out.assign(_shift_order=order)
              .sort_values(["date", "_shift_order", "is_holiday"])
              .drop(columns="_shift_order")
              .reset_index(drop=True))
    return out[columns]


# --------------------------------------------------------------------------- #
# Data profile
# --------------------------------------------------------------------------- #
def get_data_profile(df: pd.DataFrame) -> dict:
    """Data-quality report; every value is a plain Python type (JSON-safe)."""
    rows = int(len(df))
    has_data = rows > 0
    ids = df["transaction_id"] if "transaction_id" in df.columns else pd.Series(dtype="float64")

    profile: dict = {
        "raw_rows": int(df.attrs.get("raw_rows", rows)),
        "rows": rows,
        "columns": int(len(df.columns)),
        "column_names": [str(c) for c in df.columns],
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "invalid_timestamp_rows": int(df.attrs.get("invalid_timestamp_rows", 0)),
        "missing_values": {str(k): int(v) for k, v in df.isna().sum().items()},
        "duplicate_rows": int(df.duplicated().sum()),
        "null_transaction_ids": int(ids.isna().sum()),
        "duplicate_transaction_ids": int(ids.dropna().duplicated().sum()),
        "date_start": str(df["date"].min()) if has_data else None,
        "date_end": str(df["date"].max()) if has_data else None,
        "distinct_dates": int(df["date"].nunique()) if has_data else 0,
        "calendar_days": 0,
        "holiday_rows": int(df["is_holiday"].sum()),
        "holiday_names": {},
        "holiday_dates": [],
        "mixed_holiday_dates": [],
        "shift_counts": {s: int((df["shift"] == s).sum()) for s in SHIFT_ORDER},
    }

    if has_data:
        start, end = pd.to_datetime(df["date"].min()), pd.to_datetime(df["date"].max())
        profile["calendar_days"] = int((end - start).days + 1)
        per_date = df.groupby("date")["is_holiday"]
        profile["holiday_dates"] = sorted(str(d) for d in per_date.any()[lambda s: s].index)
        profile["mixed_holiday_dates"] = sorted(
            str(d) for d in per_date.nunique()[lambda s: s > 1].index
        )
    if "holiday_name" in df.columns:
        names = df.loc[df["is_holiday"], "holiday_name"].astype(str).str.strip()
        profile["holiday_names"] = {str(k): int(v) for k, v in names.value_counts().items()}
    if {"quantity", "unit_price"}.issubset(df.columns):
        profile["non_positive_quantity_or_price"] = int(
            ((df["quantity"] <= 0) | (df["unit_price"] <= 0)).sum()
        )

    try:
        agg = aggregate_invoice_counts(df)
        profile["aggregate"] = {
            "groups": int(len(agg)),
            "zero_count_groups": int((agg["invoice_count"] == 0).sum()),
            "invoice_count_total": int(agg["invoice_count"].sum()),
            "invoice_count_min": int(agg["invoice_count"].min()) if len(agg) else 0,
            "invoice_count_max": int(agg["invoice_count"].max()) if len(agg) else 0,
            "invoice_count_mean": round(float(agg["invoice_count"].mean()), 2) if len(agg) else 0.0,
            "mean_by_shift": {
                s: round(float(agg.loc[agg["shift"] == s, "invoice_count"].mean()), 2)
                for s in SHIFT_ORDER if (agg["shift"] == s).any()
            },
        }
    except ValueError as exc:
        profile["aggregate"] = {"error": str(exc)}
    return profile


# --------------------------------------------------------------------------- #
# CLI: regenerate data/processed/
# --------------------------------------------------------------------------- #
def export_processed() -> dict:
    """Write enriched CSV, aggregated CSV and data_profile.json; return the profile."""
    df = load_enriched_data(save=False)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    _save_processed(df, force=True)
    aggregate_invoice_counts(df).to_csv(AGGREGATE_PATH, index=False)
    profile = get_data_profile(df)
    PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile


if __name__ == "__main__":
    result = export_processed()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nSaved to: {PROCESSED_DIR}")
