"""Turn raw forecasts + actuals into the numbers the dashboard shows."""

from datetime import date, time

import numpy as np
import pandas as pd

from .alignment import ALIGNMENTS
from .metrics import error_metrics
from .selection import UK, select_forecasts

DEFAULT_ALIGNMENT = "linear"


def _delivery_dates(start_times: pd.Series) -> pd.Series:
    return start_times.dt.tz_convert(UK).dt.date


def join_actuals(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    a = actuals.drop_duplicates("startTime").rename(columns={"generation": "actual"})
    pairs = forecasts.merge(a[["startTime", "actual"]], on="startTime", how="inner")
    pairs["error"] = pairs["forecast"] - pairs["actual"]
    pairs["horizonHours"] = (pairs["startTime"] - pairs["publishTime"]).dt.total_seconds() / 3600
    pairs["deliveryDate"] = _delivery_dates(pairs["startTime"])
    return pairs


def in_window(df: pd.DataFrame, first_day: date | None, last_day: date | None) -> pd.DataFrame:
    keep = pd.Series(True, index=df.index)
    if first_day:
        keep &= df["deliveryDate"] >= first_day
    if last_day:
        keep &= df["deliveryDate"] <= last_day
    return df[keep]


def pair_forecasts_with_actuals(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    cutoff: time,
    first_day: date | None = None,
    last_day: date | None = None,
    alignment: str = DEFAULT_ALIGNMENT,
) -> pd.DataFrame:
    """One row per half-hour: the decision-time forecast next to the actual."""
    chosen = select_forecasts(ALIGNMENTS[alignment](forecasts), cutoff)
    pairs = join_actuals(chosen, actuals)
    return in_window(pairs, first_day, last_day).sort_values("startTime").reset_index(drop=True)


def daily_summary(pairs: pd.DataFrame) -> list[dict]:
    return [
        {"date": day.isoformat(), **error_metrics(g["forecast"], g["actual"])}
        for day, g in pairs.groupby("deliveryDate")
    ]


def by_time_of_day(pairs: pd.DataFrame) -> list[dict]:
    slot = pairs["startTime"].dt.tz_convert(UK).dt.strftime("%H:%M")
    return [
        {"slot": s, **error_metrics(g["forecast"], g["actual"])}
        for s, g in pairs.groupby(slot)
    ]


def error_histogram(pairs: pd.DataFrame, bin_mw: int = 500) -> list[dict]:
    if pairs.empty:
        return []
    err = pairs["error"].to_numpy()
    lo = np.floor(err.min() / bin_mw) * bin_mw
    hi = (np.floor(err.max() / bin_mw) + 1) * bin_mw
    counts, edges = np.histogram(err, bins=np.arange(lo, hi + bin_mw / 2, bin_mw))
    return [
        {"from": int(edges[i]), "to": int(edges[i + 1]), "count": int(c)}
        for i, c in enumerate(counts)
    ]


def horizon_profile(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    first_day: date | None = None,
    last_day: date | None = None,
    bucket_hours: int = 3,
    # Beyond ~45 h only some runs reach the slot, so buckets stop being comparable.
    max_hours: int = 45,
    alignment: str = DEFAULT_ALIGNMENT,
) -> list[dict]:
    """Accuracy of every forecast run, grouped by how far ahead it was made."""
    aligned = ALIGNMENTS[alignment](forecasts).rename(columns={"generation": "forecast"})
    pairs = in_window(join_actuals(aligned, actuals), first_day, last_day)
    pairs = pairs[(pairs["horizonHours"] > 0) & (pairs["horizonHours"] <= max_hours)]
    bucket = (np.ceil(pairs["horizonHours"] / bucket_hours) - 1) * bucket_hours
    return [
        {"fromHours": int(b), "toHours": int(b + bucket_hours), **error_metrics(g["forecast"], g["actual"])}
        for b, g in pairs.groupby(bucket)
    ]
