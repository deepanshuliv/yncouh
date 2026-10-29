"""Thin client for the two Elexon BMRS datasets the app uses."""

from datetime import date

import httpx
import pandas as pd

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


def _iso(t: pd.Timestamp) -> str:
    return t.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc(col: pd.Series) -> pd.Series:
    return pd.to_datetime(col, utc=True)


class ElexonClient:
    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(timeout=60)

    def _get(self, dataset: str, params: dict) -> list[dict]:
        resp = self.http.get(f"{BASE_URL}/datasets/{dataset}/stream", params=params)
        resp.raise_for_status()
        return resp.json()

    def wind_forecasts(self, published_from: pd.Timestamp, published_to: pd.Timestamp) -> pd.DataFrame:
        """WINDFOR: hourly national wind forecasts, every run published in the range."""
        rows = self._get(
            "WINDFOR",
            {"publishDateTimeFrom": _iso(published_from), "publishDateTimeTo": _iso(published_to)},
        )
        df = pd.DataFrame(rows, columns=["publishTime", "startTime", "generation"])
        df["publishTime"] = _utc(df["publishTime"])
        df["startTime"] = _utc(df["startTime"])
        df["generation"] = df["generation"].astype(float)
        return df.drop_duplicates(["publishTime", "startTime"]).reset_index(drop=True)

    def wind_actuals(self, first_day: date, last_day: date) -> pd.DataFrame:
        """FUELHH filtered to WIND: half-hourly actual generation by settlement date."""
        rows = self._get(
            "FUELHH",
            {
                "settlementDateFrom": first_day.isoformat(),
                "settlementDateTo": last_day.isoformat(),
                "fuelType": "WIND",
            },
        )
        df = pd.DataFrame(rows, columns=["startTime", "fuelType", "generation"])
        df = df[df["fuelType"] == "WIND"]
        out = pd.DataFrame(
            {"startTime": _utc(df["startTime"]), "generation": df["generation"].astype(float)}
        )
        return out.drop_duplicates("startTime").sort_values("startTime").reset_index(drop=True)
