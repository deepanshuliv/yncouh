import pandas as pd
import pytest


def ts(value) -> pd.Timestamp:
    """Parse a UTC timestamp written as '2026-01-14 07:30'."""
    stamp = pd.Timestamp(value)
    return stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")


def forecast_rows(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """Build a WINDFOR-shaped frame from (publishTime, startTime, generation) tuples."""
    return pd.DataFrame(
        {
            "publishTime": [ts(p) for p, _, _ in rows],
            "startTime": [ts(s) for _, s, _ in rows],
            "generation": [float(g) for _, _, g in rows],
        }
    )


def actual_rows(rows: list[tuple[str, float]]) -> pd.DataFrame:
    """Build a FUELHH(WIND)-shaped frame from (startTime, generation) tuples."""
    return pd.DataFrame(
        {
            "startTime": [ts(s) for s, _ in rows],
            "generation": [float(g) for _, g in rows],
        }
    )


@pytest.fixture
def make_forecasts():
    return forecast_rows


@pytest.fixture
def make_actuals():
    return actual_rows
