"""Which forecast did the trader actually have at decision time?

Rule: for a slot on delivery day D, use the most recent forecast whose
publishTime is at or before the cutoff (default 09:00 UK time) on D-1.

Every correct approach must pass every test here. `naive_latest` is kept as
a known-wrong baseline: it uses forecasts published after the decision and is
expected to fail the look-ahead tests.
"""

from datetime import time

import pandas as pd
import pytest

from app.selection import APPROACHES, decision_cutoffs

from .conftest import forecast_rows, ts

CORRECT = [name for name in APPROACHES if name != "naive_latest"]
NINE = time(9, 0)


def select(name, forecasts, cutoff=NINE):
    out = APPROACHES[name](forecasts, cutoff)
    return out.sort_values("startTime").reset_index(drop=True)


def value_at(selected: pd.DataFrame, start: str):
    match = selected[selected["startTime"] == ts(start)]
    assert len(match) <= 1, "one forecast per slot"
    return None if match.empty else match.iloc[0]


# --- decision cutoff -------------------------------------------------------


def test_cutoff_is_previous_day_at_cutoff_time_in_uk():
    starts = pd.Series([ts("2026-01-15 00:00"), ts("2026-01-15 23:30")])
    cutoffs = decision_cutoffs(starts, NINE)
    assert list(cutoffs) == [ts("2026-01-14 09:00"), ts("2026-01-14 09:00")]


def test_cutoff_follows_uk_local_time_during_summer_time():
    # 09:00 BST is 08:00 UTC, and 23:30 UTC on 14 Jul is already 15 Jul in the UK.
    starts = pd.Series([ts("2026-07-15 12:00"), ts("2026-07-14 23:30")])
    cutoffs = decision_cutoffs(starts, NINE)
    assert list(cutoffs) == [ts("2026-07-14 08:00"), ts("2026-07-14 08:00")]


def test_cutoff_before_spring_clock_change_uses_gmt():
    # Clocks go forward at 01:00 on 29 Mar 2026. For delivery on 30 Mar the
    # decision is 29 Mar; 00:30 that day is still GMT, 09:20 is BST.
    starts = pd.Series([ts("2026-03-30 12:00")])
    assert decision_cutoffs(starts, time(0, 30)).iloc[0] == ts("2026-03-29 00:30")
    assert decision_cutoffs(starts, time(9, 20)).iloc[0] == ts("2026-03-29 08:20")


def test_cutoff_in_skipped_spring_hour_moves_forward():
    # 01:30 on 29 Mar 2026 does not exist in the UK; treat it as 02:00 BST.
    starts = pd.Series([ts("2026-03-30 12:00")])
    assert decision_cutoffs(starts, time(1, 30)).iloc[0] == ts("2026-03-29 01:00")


def test_cutoff_in_repeated_autumn_hour_does_not_crash():
    # 01:30 happens twice on 25 Oct 2026; use the first (BST) occurrence.
    starts = pd.Series([ts("2026-10-26 12:00")])
    assert decision_cutoffs(starts, time(1, 30)).iloc[0] == ts("2026-10-25 00:30")
    assert decision_cutoffs(starts, time(9, 20)).iloc[0] == ts("2026-10-25 09:20")


# --- selection approaches --------------------------------------------------


@pytest.mark.parametrize("name", CORRECT)
def test_picks_latest_forecast_published_before_cutoff(name):
    f = forecast_rows(
        [
            ("2026-01-13 22:30", "2026-01-15 12:00", 11080),
            ("2026-01-14 04:30", "2026-01-15 12:00", 11049),
            ("2026-01-14 07:30", "2026-01-15 12:00", 11050),
        ]
    )
    row = value_at(select(name, f), "2026-01-15 12:00")
    assert row["forecast"] == 11050
    assert row["publishTime"] == ts("2026-01-14 07:30")


@pytest.mark.parametrize("name", CORRECT)
def test_ignores_forecasts_published_after_cutoff(name):
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 11049),
            ("2026-01-14 09:30", "2026-01-15 12:00", 11178),
            ("2026-01-15 07:30", "2026-01-15 12:00", 9800),
        ]
    )
    assert value_at(select(name, f), "2026-01-15 12:00")["forecast"] == 11049


def test_naive_baseline_leaks_future_forecasts():
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 11049),
            ("2026-01-15 07:30", "2026-01-15 12:00", 9800),
        ]
    )
    assert value_at(select("naive_latest", f), "2026-01-15 12:00")["forecast"] == 9800


@pytest.mark.parametrize("name", CORRECT)
def test_forecast_published_exactly_at_cutoff_counts(name):
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 1),
            ("2026-01-14 09:00", "2026-01-15 12:00", 2),
        ]
    )
    assert value_at(select(name, f), "2026-01-15 12:00")["forecast"] == 2


@pytest.mark.parametrize("name", CORRECT)
def test_each_delivery_day_uses_its_own_cutoff(name):
    # One publish run covers two delivery days. The 15 Jan 07:30 run is too
    # late for 15 Jan but is the right one for 16 Jan.
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 100),
            ("2026-01-14 07:30", "2026-01-16 12:00", 200),
            ("2026-01-15 07:30", "2026-01-15 12:00", 110),
            ("2026-01-15 07:30", "2026-01-16 12:00", 210),
        ]
    )
    selected = select(name, f)
    assert value_at(selected, "2026-01-15 12:00")["forecast"] == 100
    assert value_at(selected, "2026-01-16 12:00")["forecast"] == 210


@pytest.mark.parametrize("name", CORRECT)
def test_irregular_publish_time_is_handled(name):
    # Real data contains an off-schedule run at 12:25.
    f = forecast_rows(
        [
            ("2026-01-13 11:30", "2026-01-15 12:00", 1),
            ("2026-01-13 12:25", "2026-01-15 12:00", 2),
            ("2026-01-13 15:30", "2026-01-15 12:00", 3),
        ]
    )
    assert value_at(select(name, f), "2026-01-15 12:00")["forecast"] == 3


@pytest.mark.parametrize("name", CORRECT)
def test_slot_without_any_eligible_forecast_is_dropped(name):
    f = forecast_rows([("2026-01-14 10:00", "2026-01-15 12:00", 1)])
    assert value_at(select(name, f), "2026-01-15 12:00") is None


@pytest.mark.parametrize("name", CORRECT)
def test_cutoff_time_is_configurable(name):
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 1),
            ("2026-01-14 09:30", "2026-01-15 12:00", 2),
        ]
    )
    assert value_at(select(name, f, time(7, 0)), "2026-01-15 12:00") is None
    assert value_at(select(name, f, time(9, 0)), "2026-01-15 12:00")["forecast"] == 1
    assert value_at(select(name, f, time(11, 0)), "2026-01-15 12:00")["forecast"] == 2


@pytest.mark.parametrize("name", CORRECT)
def test_duplicate_rows_do_not_duplicate_slots(name):
    f = forecast_rows(
        [
            ("2026-01-14 07:30", "2026-01-15 12:00", 5),
            ("2026-01-14 07:30", "2026-01-15 12:00", 5),
        ]
    )
    selected = select(name, f)
    assert len(selected) == 1


@pytest.mark.parametrize("name", CORRECT)
def test_output_columns(name):
    f = forecast_rows([("2026-01-14 07:30", "2026-01-15 12:00", 5)])
    assert list(select(name, f).columns) == ["startTime", "publishTime", "forecast"]


@pytest.mark.parametrize("name", CORRECT)
def test_all_correct_approaches_agree_on_a_dense_case(name):
    publishes = pd.date_range("2026-01-12 02:30", "2026-01-16 22:30", freq="3h", tz="UTC")
    rows = []
    for p in publishes:
        for s in pd.date_range(p.ceil("h"), periods=60, freq="h"):
            rows.append((p, s, float(p.value % 997 + s.hour)))
    f = pd.DataFrame(rows, columns=["publishTime", "startTime", "generation"])

    reference = select("python_loop", f)
    pd.testing.assert_frame_equal(select(name, f), reference)
