"""Pick the forecast a trader actually had when making a day-ahead decision.

For a slot on delivery day D (UK calendar day), the decision is made on D-1 at
the cutoff time (UK clock). The usable forecast is the most recent one whose
publishTime is at or before that cutoff.

Several implementations are kept so they can be compared on the same tests
and benchmark (see scripts/compare_approaches.py). `select_forecasts` is the
one the app uses.
"""

from datetime import time
from typing import Callable

import pandas as pd

UK = "Europe/London"
COLUMNS = ["startTime", "publishTime", "forecast"]

Selector = Callable[[pd.DataFrame, time], pd.DataFrame]


def decision_cutoffs(start_times: pd.Series, cutoff: time) -> pd.Series:
    """UTC decision deadline for each slot: D-1 at `cutoff` UK time."""
    # Work in naive UK wall-clock time, then attach the offset that applies on
    # D-1 at the cutoff (not the offset of D, which differs on clock-change days).
    delivery_day = start_times.dt.tz_convert(UK).dt.tz_localize(None).dt.normalize()
    wall_clock = delivery_day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff.hour, minutes=cutoff.minute)
    local = wall_clock.dt.tz_localize(UK, ambiguous=True, nonexistent="shift_forward")
    return local.dt.tz_convert("UTC")


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"generation": "forecast"})[COLUMNS]
    return out.sort_values("startTime").reset_index(drop=True)


def naive_latest(forecasts: pd.DataFrame, cutoff: time) -> pd.DataFrame:
    """WRONG on purpose: newest forecast overall, ignoring the decision time."""
    latest = forecasts.sort_values("publishTime").drop_duplicates("startTime", keep="last")
    return _finish(latest)


def python_loop(forecasts: pd.DataFrame, cutoff: time) -> pd.DataFrame:
    """Plain-Python reference implementation: easy to read, slow."""
    deadlines = decision_cutoffs(forecasts["startTime"], cutoff)
    best: dict = {}
    for row, deadline in zip(forecasts.itertuples(index=False), deadlines):
        if row.publishTime > deadline:
            continue
        current = best.get(row.startTime)
        if current is None or row.publishTime > current[0]:
            best[row.startTime] = (row.publishTime, row.generation)
    rows = [(s, p, g) for s, (p, g) in best.items()]
    return _finish(pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"]))


def filter_sort(forecasts: pd.DataFrame, cutoff: time) -> pd.DataFrame:
    """Vectorised: drop rows published after the deadline, keep the newest per slot."""
    eligible = forecasts[forecasts["publishTime"] <= decision_cutoffs(forecasts["startTime"], cutoff)]
    latest = eligible.sort_values(["startTime", "publishTime"]).drop_duplicates(
        "startTime", keep="last"
    )
    return _finish(latest)


def merge_asof(forecasts: pd.DataFrame, cutoff: time) -> pd.DataFrame:
    """As-of join: for each slot's deadline, take the last publish at or before it."""
    slots = pd.DataFrame({"startTime": forecasts["startTime"].drop_duplicates()})
    slots["deadline"] = decision_cutoffs(slots["startTime"], cutoff)
    runs = forecasts.drop_duplicates(["startTime", "publishTime"]).sort_values("publishTime")
    joined = pd.merge_asof(
        slots.sort_values("deadline"),
        runs,
        left_on="deadline",
        right_on="publishTime",
        by="startTime",
        direction="backward",
    )
    return _finish(joined.dropna(subset=["publishTime"]))


APPROACHES: dict[str, Selector] = {
    "naive_latest": naive_latest,
    "python_loop": python_loop,
    "filter_sort": filter_sort,
    "merge_asof": merge_asof,
}

select_forecasts: Selector = filter_sort
