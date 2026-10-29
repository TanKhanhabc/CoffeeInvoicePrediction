import json

import pandas as pd
import pytest

from app.services import data_service as ds
from app.services.data_service import (
    RAW_PATH,
    SHIFT_ORDER,
    aggregate_invoice_counts,
    enrich,
    get_data_profile,
    # temp eda
    get_eda_summary,
    load_enriched_data,
    shift_from_hour,
)


def make_raw(rows):
    """rows: (transaction_id, timestamp, holiday_name)"""
    return pd.DataFrame(rows, columns=["transaction_id", "timestamp", "holiday_name"])


def write_csv(tmp_path, rows):
    path = tmp_path / "sales.csv"
    make_raw(rows).to_csv(path, index=False)
    return path


# ----------------------------- shift ------------------------------------- #
def test_shift_boundaries():
    assert shift_from_hour(0) == "Night"
    assert shift_from_hour(5) == "Night"
    assert shift_from_hour(6) == "Morning"
    assert shift_from_hour(11) == "Morning"
    assert shift_from_hour(12) == "Afternoon"
    assert shift_from_hour(16) == "Afternoon"
    assert shift_from_hour(17) == "Evening"
    assert shift_from_hour(23) == "Evening"


@pytest.mark.parametrize("hour", [-1, 24, 99])
def test_shift_rejects_invalid_hour(hour):
    with pytest.raises(ValueError):
        shift_from_hour(hour)


def test_vectorised_shift_matches_scalar_for_every_hour():
    raw = make_raw([(i, f"2023-01-01 {i:02d}:30:00", None) for i in range(24)])
    df = enrich(raw)
    assert list(df["shift"]) == [shift_from_hour(h) for h in range(24)]


def test_shift_edges_use_exact_timestamps():
    raw = make_raw([
        (1, "2023-01-01 05:59:59", None),
        (2, "2023-01-01 06:00:00", None),
        (3, "2023-01-01 16:59:59", None),
        (4, "2023-01-01 17:00:00", None),
        (5, "2023-01-01 23:59:59", None),
        (6, "2023-01-01 00:00:00", None),
    ])
    assert list(enrich(raw)["shift"]) == [
        "Night", "Morning", "Afternoon", "Evening", "Evening", "Night"
    ]


# ----------------------------- is_holiday -------------------------------- #
def test_is_holiday_rules():
    raw = make_raw([
        (1, "2023-01-01 08:00:00", "New Year's Day"),
        (2, "2023-01-02 08:00:00", None),
        (3, "2023-01-03 08:00:00", ""),
        (4, "2023-01-04 08:00:00", "   "),
    ])
    df = enrich(raw)
    assert list(df["is_holiday"]) == [True, False, False, False]
    assert df["is_holiday"].dtype == bool


def test_is_holiday_false_when_column_missing():
    raw = make_raw([(1, "2023-01-01 08:00:00", None)]).drop(columns="holiday_name")
    assert not enrich(raw)["is_holiday"].any()


# ----------------------------- loading ----------------------------------- #
def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_enriched_data(tmp_path / "nope.csv")


def test_load_missing_required_column_raises(tmp_path):
    path = tmp_path / "bad.csv"
    pd.DataFrame({"transaction_id": [1]}).to_csv(path, index=False)
    with pytest.raises(ValueError, match="timestamp"):
        load_enriched_data(path)


def test_invalid_timestamps_are_dropped_and_counted(tmp_path):
    path = write_csv(tmp_path, [
        (1, "2023-01-01 08:00:00", None),
        (2, "not-a-date", None),
        (3, "2023-01-01 09:00:00", None),
    ])
    df = load_enriched_data(path)
    assert len(df) == 2
    profile = get_data_profile(df)
    assert profile["raw_rows"] == 3
    assert profile["rows"] == 2
    assert profile["invalid_timestamp_rows"] == 1


def test_load_returns_independent_copies(tmp_path):
    path = write_csv(tmp_path, [(1, "2023-01-01 08:00:00", None)])
    first = load_enriched_data(path)
    first["shift"] = "CHANGED"
    assert load_enriched_data(path)["shift"].iloc[0] == "Morning"


def test_load_does_not_touch_processed_dir_for_custom_path(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, "PROCESSED_PATH", tmp_path / "out" / "enriched.csv")
    path = write_csv(tmp_path, [(1, "2023-01-01 08:00:00", None)])
    load_enriched_data(path)
    assert not (tmp_path / "out").exists()


# ----------------------------- aggregation ------------------------------- #
def test_aggregate_counts_unique_transaction_ids():
    raw = make_raw([
        (1, "2023-01-01 08:00:00", None),
        (2, "2023-01-01 09:00:00", None),
        (2, "2023-01-01 09:00:00", None),  # same invoice repeated -> counted once
        (3, "2023-01-01 13:00:00", None),
    ])
    agg = aggregate_invoice_counts(enrich(raw))
    by_shift = agg.set_index("shift")["invoice_count"]
    assert by_shift["Morning"] == 2
    assert by_shift["Afternoon"] == 1


def test_aggregate_fills_all_shifts_and_calendar_days_with_zero():
    raw = make_raw([
        (1, "2023-01-01 08:00:00", None),
        (2, "2023-01-03 20:00:00", None),  # 2023-01-02 has no transactions
    ])
    agg = aggregate_invoice_counts(enrich(raw))
    assert len(agg) == 3 * 4
    assert list(agg["date"].unique()) == ["2023-01-01", "2023-01-02", "2023-01-03"]
    assert (agg.loc[agg["date"] == "2023-01-02", "invoice_count"] == 0).all()
    assert agg["invoice_count"].sum() == 2


def test_aggregate_without_fill_keeps_only_observed_groups():
    raw = make_raw([(1, "2023-01-01 08:00:00", None)])
    agg = aggregate_invoice_counts(enrich(raw), fill_missing=False)
    assert len(agg) == 1


def test_aggregate_sorted_by_date_then_shift_order():
    raw = make_raw([(i, f"2023-01-0{d} {h:02d}:00:00", None)
                    for i, (d, h) in enumerate([(2, 20), (1, 8), (1, 2), (2, 13)])])
    agg = aggregate_invoice_counts(enrich(raw))
    assert list(agg["shift"].head(4)) == SHIFT_ORDER
    assert list(agg["date"]) == sorted(agg["date"])


def test_aggregate_output_types():
    raw = make_raw([(1, "2023-01-01 08:00:00", "New Year's Day")])
    agg = aggregate_invoice_counts(enrich(raw))
    assert list(agg.columns) == [
        "date", "shift", "is_holiday", "invoice_count", "day_of_week", "month"
    ]
    assert agg["date"].map(type).eq(str).all()
    assert agg["is_holiday"].dtype == bool
    assert pd.api.types.is_integer_dtype(agg["invoice_count"])
    assert not agg.duplicated(["date", "shift", "is_holiday"]).any()


def test_mixed_holiday_date_is_one_row_per_shift_in_date_mode():
    # 4 July: only the US row is a holiday, the UK row on the same date is not.
    raw = make_raw([
        (1, "2023-07-04 08:00:00", "Independence Day"),
        (2, "2023-07-04 08:30:00", None),
        (3, "2023-07-04 09:00:00", None),
    ])
    agg = aggregate_invoice_counts(enrich(raw))
    morning = agg[(agg["date"] == "2023-07-04") & (agg["shift"] == "Morning")]
    assert len(morning) == 1
    assert morning["invoice_count"].iloc[0] == 3
    assert bool(morning["is_holiday"].iloc[0]) is True


def test_mixed_holiday_date_is_split_in_row_mode():
    raw = make_raw([
        (1, "2023-07-04 08:00:00", "Independence Day"),
        (2, "2023-07-04 08:30:00", None),
    ])
    agg = aggregate_invoice_counts(enrich(raw), holiday_mode="row")
    assert len(agg) == 2
    assert agg["invoice_count"].tolist() == [1, 1]


def test_invalid_holiday_mode_raises():
    with pytest.raises(ValueError):
        aggregate_invoice_counts(enrich(make_raw([(1, "2023-01-01 08:00:00", None)])),
                                 holiday_mode="x")


def test_aggregate_empty_frame():
    empty = enrich(make_raw([(1, "bad", None)]))
    assert aggregate_invoice_counts(empty).empty


# ----------------------------- eda -------------------------------------- #
def test_eda_summary_collects_key_insights():
    raw = make_raw([
        (1, "2023-12-25 08:00:00", "Christmas Day"),
        (2, "2023-12-25 12:00:00", None),
        (3, "2023-12-26 09:00:00", "Boxing Day"),
        (4, "2023-12-26 18:00:00", None),
    ])
    summary = get_eda_summary(enrich(raw))
    assert summary["rows"] == 4
    assert summary["shift_distribution"]["Morning"] == 2
    assert summary["holiday_share_pct"] == pytest.approx(50.0)
    assert summary["top_products"] == []
    assert summary["day_of_week_distribution"]["Monday"] == 2


# ----------------------------- profile ----------------------------------- #
def test_profile_is_json_serialisable_and_complete():
    raw = make_raw([
        (1, "2023-12-25 08:00:00", "Christmas Day"),
        (2, "2023-12-26 09:00:00", "Boxing Day"),
        (3, "2023-12-26 09:10:00", None),
        (3, "2023-12-26 09:10:00", None),  # duplicate transaction_id
    ])
    profile = get_data_profile(enrich(raw))
    json.dumps(profile)  # must not raise (FastAPI returns this dict as-is)
    assert profile["rows"] == 4
    assert profile["duplicate_transaction_ids"] == 1
    assert profile["duplicate_rows"] == 1
    assert profile["null_transaction_ids"] == 0
    assert profile["date_start"] == "2023-12-25"
    assert profile["calendar_days"] == 2
    assert profile["holiday_rows"] == 2
    assert profile["holiday_dates"] == ["2023-12-25", "2023-12-26"]
    assert profile["mixed_holiday_dates"] == ["2023-12-26"]
    assert profile["shift_counts"]["Morning"] == 4
    assert set(profile["shift_counts"]) == set(SHIFT_ORDER)
    assert profile["aggregate"]["groups"] == 2 * 4


def test_profile_keeps_keys_used_by_existing_routes():
    profile = get_data_profile(enrich(make_raw([(1, "2023-01-01 08:00:00", None)])))
    for key in ("rows", "columns", "column_names", "missing_values",
                "duplicate_rows", "holiday_rows", "shift_counts"):
        assert key in profile


# ----------------------------- integration ------------------------------- #
def test_output_is_accepted_by_ml_module():
    model_service = pytest.importorskip("app.ml.model_service")
    raw = make_raw([(i, f"2023-01-{1 + i // 4:02d} {h:02d}:00:00", None)
                    for i, h in enumerate([2, 8, 13, 20] * 6)])
    grouped = aggregate_invoice_counts(enrich(raw))
    prepared = model_service.prepare_aggregates(grouped)
    assert len(prepared) == len(grouped)


@pytest.mark.skipif(not RAW_PATH.exists(), reason="data/raw/coffee_shop_sales.csv not found")
def test_real_dataset_matches_known_profile():
    df = load_enriched_data(save=False)
    profile = get_data_profile(df)
    assert profile["rows"] == 20000
    assert profile["invalid_timestamp_rows"] == 0
    assert profile["duplicate_transaction_ids"] == 0
    assert profile["date_start"] == "2023-01-01"
    assert profile["date_end"] == "2023-12-31"
    assert profile["holiday_rows"] == 335
    assert profile["shift_counts"] == {
        "Night": 1510, "Morning": 9806, "Afternoon": 5982, "Evening": 2702
    }
    agg = aggregate_invoice_counts(df)
    assert len(agg) == 365 * 4
    assert agg["invoice_count"].sum() == 20000
    assert not agg.duplicated(["date", "shift"]).any()
