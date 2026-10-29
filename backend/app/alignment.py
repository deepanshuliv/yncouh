"""Bring hourly WINDFOR forecasts onto the half-hourly FUELHH grid.

Each approach works within a single forecast run (one publishTime) so values
from different runs are never blended.
"""

from typing import Callable

import pandas as pd

HOUR = pd.Timedelta(hours=1)
HALF_HOUR = pd.Timedelta(minutes=30)

Aligner = Callable[[pd.DataFrame], pd.DataFrame]


def hourly(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Leave forecasts hourly; half-hour actuals simply go unmatched."""
    return forecasts.drop_duplicates(["publishTime", "startTime"]).reset_index(drop=True)


def _half_hours(forecasts: pd.DataFrame, value) -> pd.DataFrame:
    """Add an :30 point after each hour whose next hour is in the same run."""
    f = hourly(forecasts).sort_values(["publishTime", "startTime"])
    nxt = f.groupby("publishTime")["startTime"].shift(-1)
    nxt_gen = f.groupby("publishTime")["generation"].shift(-1)
    has_next = (nxt - f["startTime"]) == HOUR
    halves = pd.DataFrame(
        {
            "publishTime": f["publishTime"][has_next],
            "startTime": f["startTime"][has_next] + HALF_HOUR,
            "generation": value(f["generation"], nxt_gen)[has_next],
        }
    )
    return (
        pd.concat([f, halves], ignore_index=True)
        .sort_values(["publishTime", "startTime"])
        .reset_index(drop=True)
    )


def hold(forecasts: pd.DataFrame) -> pd.DataFrame:
    """xx:30 repeats the xx:00 value (step function)."""
    return _half_hours(forecasts, lambda this, nxt: this)


def linear(forecasts: pd.DataFrame) -> pd.DataFrame:
    """xx:30 is the midpoint of xx:00 and the next hour."""
    return _half_hours(forecasts, lambda this, nxt: (this + nxt) / 2)


ALIGNMENTS: dict[str, Aligner] = {"hourly": hourly, "hold": hold, "linear": linear}
