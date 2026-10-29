from datetime import date, time

import pandas as pd
import pytest

from app.analysis import (
    by_time_of_day,
    daily_summary,
    error_histogram,
    horizon_profile,
    pair_forecasts_with_actuals,
)

from .conftest import actual_rows, forecast_rows, ts

NINE = time(9, 0)


@pytest.fixture
def forecasts():
    # Two runs covering 15 Jan 12:00-13:00. Only the 07:30 run is before cutoff.
    return forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 1000),
            ("2026-01-14 07:30", "2026-01-15 13:00", 2000),
            ("2026-01-14 11:30", "2026-01-15 12:00", 5000),
            ("2026-01-14 11:30", "2026-01-15 13:00", 5000),
        ]
    )


@pytest.fixture
def actuals():
    return actual_rows(
        [
            ("2026-01-15 12:00", 1100),
            ("2026-01-15 12:30", 1400),
            ("2026-01-15 13:00", 1900),
            ("2026-01-15 13:30", 1900),  # no forecast can cover this slot
        ]
    )


def test_pairs_use_decision_time_forecast_and_compute_error(forecasts, actuals):
    pairs = pair_forecasts_with_actuals(forecasts, actuals, NINE)
    assert list(pairs["startTime"]) == [
        ts("2026-01-15 12:00"),
        ts("2026-01-15 12:30"),
        ts("2026-01-15 13:00"),
    ]
    assert list(pairs["forecast"]) == [1000, 1500, 2000]
    assert list(pairs["error"]) == [-100, 100, 100]
    assert set(pairs["publishTime"]) == {ts("2026-01-14 07:30")}


def test_pairs_carry_delivery_date_and_horizon(forecasts, actuals):
    pairs = pair_forecasts_with_actuals(forecasts, actuals, NINE)
    assert set(pairs["deliveryDate"]) == {date(2026, 1, 15)}
    # 07:30 on 14 Jan -> 12:00 on 15 Jan is 28.5 hours ahead.
    assert pairs.iloc[0]["horizonHours"] == pytest.approx(28.5)


def test_pairs_can_be_limited_to_delivery_window(forecasts, actuals):
    pairs = pair_forecasts_with_actuals(
        forecasts, actuals, NINE, first_day=date(2026, 1, 16), last_day=date(2026, 1, 20)
    )
    assert pairs.empty


def test_daily_summary(forecasts, actuals):
    pairs = pair_forecasts_with_actuals(forecasts, actuals, NINE)
    days = daily_summary(pairs)
    assert len(days) == 1
    assert days[0]["date"] == "2026-01-15"
    assert days[0]["mae"] == pytest.approx(100)
    assert days[0]["count"] == 3


def test_by_time_of_day_groups_by_uk_clock_slot(forecasts, actuals):
    pairs = pair_forecasts_with_actuals(forecasts, actuals, NINE)
    slots = {row["slot"]: row for row in by_time_of_day(pairs)}
    assert set(slots) == {"12:00", "12:30", "13:00"}
    assert slots["12:00"]["bias"] == pytest.approx(-100)


def test_error_histogram_counts_every_pair(forecasts, actuals):
    pairs = pair_forecasts_with_actuals(forecasts, actuals, NINE)
    bins = error_histogram(pairs, bin_mw=100)
    assert sum(b["count"] for b in bins) == 3
    assert all(b["to"] - b["from"] == 100 for b in bins)


def test_horizon_profile_uses_every_run_and_buckets_by_lead_time(forecasts, actuals):
    profile = horizon_profile(forecasts, actuals, bucket_hours=6)
    # 07:30 run is 28.5-29.5h ahead -> bucket 24-30; 11:30 run is 24.5-25.5h -> bucket 24-30.
    assert [b["fromHours"] for b in profile] == [24]
    assert profile[0]["count"] == 6


def test_horizon_profile_stops_at_max_hours(forecasts, actuals):
    assert horizon_profile(forecasts, actuals, bucket_hours=6, max_hours=24) == []


def test_horizon_profile_skips_hindcasts():
    f = forecast_rows([("2026-01-15 14:00", "2026-01-15 12:00", 1)])
    a = actual_rows([("2026-01-15 12:00", 1)])
    assert horizon_profile(f, a) == []
