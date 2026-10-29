"""HTTP API for the wind forecast dashboard."""

import os
from datetime import date, time
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import analysis
from .data import Dataset, load_dataset
from .metrics import error_metrics
from .selection import UK, decision_cutoffs

# GB day-ahead auctions close at 09:20 (EPEX SPOT) and 09:50 (Nord Pool N2EX) UK time.
# Bids must be in by the earlier close, so that is the default decision time.
DEFAULT_CUTOFF = "09:20"
CUTOFF_PRESETS = [
    {"time": "09:20", "label": "EPEX SPOT GB day-ahead gate closure"},
    {"time": "09:50", "label": "Nord Pool N2EX day-ahead gate closure"},
]
CUTOFF = Query(DEFAULT_CUTOFF, pattern=r"^([01]\d|2[0-3]):[0-5]\d$", description="UK time on D-1")


def _iso(t: pd.Timestamp) -> str:
    return t.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_cutoff(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def create_app(data: Dataset | None = None) -> FastAPI:
    data = data or load_dataset()
    app = FastAPI(title="Wind Forecast Monitor")

    @lru_cache(maxsize=32)
    def pairs_for(cutoff: str) -> pd.DataFrame:
        return analysis.pair_forecasts_with_actuals(
            data.forecasts, data.actuals, _parse_cutoff(cutoff), data.first_day, data.last_day
        )

    @lru_cache(maxsize=1)
    def horizon_buckets() -> list[dict]:
        return analysis.horizon_profile(data.forecasts, data.actuals, data.first_day, data.last_day)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/meta")
    def meta():
        runs = pd.Series(data.forecasts["publishTime"].unique()).dt.strftime("%H:%M").value_counts()
        return {
            "firstDeliveryDay": data.first_day.isoformat(),
            "lastDeliveryDay": data.last_day.isoformat(),
            "defaultCutoff": DEFAULT_CUTOFF,
            "cutoffPresets": CUTOFF_PRESETS,
            "alignment": analysis.DEFAULT_ALIGNMENT,
            # Regular WINDFOR run times (UTC); ignore one-off runs.
            "forecastRunTimes": sorted(runs[runs > 1].index.tolist()),
        }

    @app.get("/api/day")
    def day(delivery: date = Query(alias="date"), cutoff: str = CUTOFF):
        if not data.first_day <= delivery <= data.last_day:
            raise HTTPException(404, f"{delivery} is outside the analysed delivery window")
        pairs = pairs_for(cutoff)
        today = pairs[pairs["deliveryDate"] == delivery]
        midnight = pd.Series([pd.Timestamp(delivery, tz=UK)])
        return {
            "date": delivery.isoformat(),
            "decisionTime": _iso(decision_cutoffs(midnight, _parse_cutoff(cutoff)).iloc[0]),
            "forecastRuns": [_iso(t) for t in sorted(today["publishTime"].unique())],
            "metrics": error_metrics(today["forecast"], today["actual"]),
            "points": [
                {
                    "time": _iso(r.startTime),
                    "forecast": r.forecast,
                    "actual": r.actual,
                    "error": r.error,
                    "horizonHours": r.horizonHours,
                }
                for r in today.itertuples()
            ],
        }

    @app.get("/api/summary")
    def summary(cutoff: str = CUTOFF):
        pairs = pairs_for(cutoff)
        return {
            "cutoff": cutoff,
            "overall": error_metrics(pairs["forecast"], pairs["actual"]),
            "meanActual": float(pairs["actual"].mean()) if len(pairs) else None,
            "daily": analysis.daily_summary(pairs),
            "byTimeOfDay": analysis.by_time_of_day(pairs),
            "histogram": analysis.error_histogram(pairs),
        }

    @app.get("/api/horizon")
    def horizon(cutoff: str = CUTOFF):
        pairs = pairs_for(cutoff)
        used = None
        if len(pairs):
            used = {"min": float(pairs["horizonHours"].min()), "max": float(pairs["horizonHours"].max())}
        return {"buckets": horizon_buckets(), "decisionHorizon": used}

    dist = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app
