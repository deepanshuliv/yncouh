"""The January 2026 dataset: config, on-disk cache and loading."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FORECASTS_CSV = DATA_DIR / "windfor.csv"
ACTUALS_CSV = DATA_DIR / "fuelhh_wind.csv"

# Purchase decisions made 1-31 Jan 2026 -> delivery 2 Jan to 1 Feb.
FIRST_DELIVERY_DAY = date(2026, 1, 2)
LAST_DELIVERY_DAY = date(2026, 2, 1)
# Runs published from a few days before the first delivery day are needed for
# the horizon analysis (forecasts look up to ~3 days ahead).
FORECASTS_PUBLISHED_FROM = pd.Timestamp("2025-12-29", tz="UTC")
FORECASTS_PUBLISHED_TO = pd.Timestamp("2026-02-02", tz="UTC")


@dataclass(frozen=True)
class Dataset:
    forecasts: pd.DataFrame  # publishTime, startTime, generation (hourly)
    actuals: pd.DataFrame  # startTime, generation (half-hourly)
    first_day: date = FIRST_DELIVERY_DAY
    last_day: date = LAST_DELIVERY_DAY


def load_dataset() -> Dataset:
    if not (FORECASTS_CSV.exists() and ACTUALS_CSV.exists()):
        raise FileNotFoundError(
            f"No cached data in {DATA_DIR}. Run: python -m scripts.fetch_data"
        )
    forecasts = pd.read_csv(FORECASTS_CSV, parse_dates=["publishTime", "startTime"])
    actuals = pd.read_csv(ACTUALS_CSV, parse_dates=["startTime"])
    return Dataset(forecasts=forecasts, actuals=actuals)


def save_dataset(forecasts: pd.DataFrame, actuals: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    forecasts.to_csv(FORECASTS_CSV, index=False, date_format=fmt)
    actuals.to_csv(ACTUALS_CSV, index=False, date_format=fmt)
