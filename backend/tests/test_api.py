from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.data import Dataset
from app.main import create_app

from .conftest import ts


@pytest.fixture
def client():
    # Two delivery days (15-16 Jan) with hourly forecasts from two runs a day.
    hours = pd.date_range("2026-01-15 00:00", "2026-01-17 00:00", freq="h", tz="UTC")
    runs = pd.date_range("2026-01-13 07:30", "2026-01-16 07:30", freq="12h", tz="UTC")
    forecasts = pd.DataFrame(
        [(r, h, 5000.0) for r in runs for h in hours if h > r],
        columns=["publishTime", "startTime", "generation"],
    )
    slots = pd.date_range("2026-01-15 00:00", "2026-01-16 23:30", freq="30min", tz="UTC")
    actuals = pd.DataFrame({"startTime": slots, "generation": 4800.0})
    data = Dataset(
        forecasts=forecasts,
        actuals=actuals,
        first_day=date(2026, 1, 15),
        last_day=date(2026, 1, 16),
    )
    return TestClient(create_app(data))


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["firstDeliveryDay"] == "2026-01-15"
    assert body["lastDeliveryDay"] == "2026-01-16"
    assert body["defaultCutoff"] == "09:20"
    assert [p["time"] for p in body["cutoffPresets"]] == ["09:20", "09:50"]


def test_day_returns_48_half_hours(client):
    body = client.get("/api/day", params={"date": "2026-01-15"}).json()
    assert len(body["points"]) == 48
    first = body["points"][0]
    assert first["forecast"] == 5000 and first["actual"] == 4800 and first["error"] == 200
    assert body["metrics"]["bias"] == pytest.approx(200)
    assert body["decisionTime"] == "2026-01-14T09:20:00Z"
    assert body["forecastRuns"] == ["2026-01-14T07:30:00Z"]


def test_day_respects_cutoff(client):
    # A 07:00 cutoff is before the 07:30 run, so the previous evening's run is used.
    body = client.get("/api/day", params={"date": "2026-01-15", "cutoff": "07:00"}).json()
    assert body["forecastRuns"] == ["2026-01-13T19:30:00Z"]
    body = client.get("/api/day", params={"date": "2026-01-16", "cutoff": "07:00"}).json()
    assert body["forecastRuns"] == ["2026-01-14T19:30:00Z"]


def test_day_outside_window_is_404(client):
    assert client.get("/api/day", params={"date": "2026-03-01"}).status_code == 404


@pytest.mark.parametrize("bad", ["9am", "25:00", "09:61", ""])
def test_invalid_cutoff_is_422(client, bad):
    assert client.get("/api/summary", params={"cutoff": bad}).status_code == 422


def test_summary_shape(client):
    body = client.get("/api/summary").json()
    assert body["overall"]["count"] == 96
    assert body["overall"]["bias"] == pytest.approx(200)
    assert len(body["daily"]) == 2
    assert len(body["byTimeOfDay"]) == 48
    assert body["histogram"]


def test_horizon(client):
    body = client.get("/api/horizon").json()
    assert body["buckets"]
    assert all(b["mae"] == pytest.approx(200) for b in body["buckets"])
