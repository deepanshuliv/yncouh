"""WINDFOR is hourly, FUELHH is half-hourly. Each alignment approach turns a
forecast run into values that can be compared with half-hourly actuals."""

import pandas as pd
import pytest

from app.alignment import ALIGNMENTS

from .conftest import forecast_rows, ts


def run(*values, start="2026-01-15 10:00", publish="2026-01-14 07:30"):
    """One forecast run with consecutive hourly values starting at `start`."""
    hours = pd.date_range(ts(start), periods=len(values), freq="h")
    return forecast_rows([(publish, str(h), v) for h, v in zip(hours, values)])


def lookup(df, start, publish="2026-01-14 07:30"):
    hit = df[(df["startTime"] == ts(start)) & (df["publishTime"] == ts(publish))]
    return None if hit.empty else hit.iloc[0]["generation"]


def test_hourly_keeps_only_hourly_points():
    out = ALIGNMENTS["hourly"](run(100, 200))
    assert len(out) == 2
    assert lookup(out, "2026-01-15 10:30") is None


def test_hold_repeats_hour_value_for_half_hour():
    out = ALIGNMENTS["hold"](run(100, 200, 400))
    assert lookup(out, "2026-01-15 10:30") == 100
    assert lookup(out, "2026-01-15 11:30") == 200


@pytest.mark.parametrize("name", ["hold", "linear"])
def test_half_hour_methods_fill_the_same_slots(name):
    # Same coverage keeps the comparison between methods fair.
    out = ALIGNMENTS[name](run(100, 200))
    assert lookup(out, "2026-01-15 10:30") is not None
    assert lookup(out, "2026-01-15 11:30") is None


def test_linear_uses_midpoint_between_hours():
    out = ALIGNMENTS["linear"](run(100, 200, 400))
    assert lookup(out, "2026-01-15 10:00") == 100
    assert lookup(out, "2026-01-15 10:30") == 150
    assert lookup(out, "2026-01-15 11:30") == 300


def test_linear_does_not_extrapolate_past_last_hour():
    out = ALIGNMENTS["linear"](run(100, 200))
    assert lookup(out, "2026-01-15 11:30") is None


@pytest.mark.parametrize("name", ["hold", "linear"])
def test_never_mixes_two_forecast_runs(name):
    a = run(100, 200, publish="2026-01-14 04:30")
    b = run(1000, 2000, publish="2026-01-14 07:30")
    out = ALIGNMENTS[name](pd.concat([a, b]))
    assert lookup(out, "2026-01-15 10:30", publish="2026-01-14 04:30") in (100, 150)
    assert lookup(out, "2026-01-15 10:30", publish="2026-01-14 07:30") in (1000, 1500)


@pytest.mark.parametrize("name", ["hold", "linear"])
def test_does_not_bridge_gaps_in_a_run(name):
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 10:00", 100),
            ("2026-01-14 07:30", "2026-01-15 13:00", 400),
        ]
    )
    out = ALIGNMENTS[name](f)
    assert lookup(out, "2026-01-15 11:30") is None
