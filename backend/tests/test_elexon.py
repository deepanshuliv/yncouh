import httpx
import pandas as pd

from app.elexon import ElexonClient

from .conftest import ts


def client_with(handler):
    return ElexonClient(http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_fetch_wind_forecasts_parses_and_dedupes():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = request.url
        row = {
            "dataset": "WINDFOR",
            "publishTime": "2026-01-14T07:30:00Z",
            "startTime": "2026-01-15T12:00:00Z",
            "generation": 11049,
        }
        return httpx.Response(200, json=[row, row])

    df = client_with(handler).wind_forecasts(ts("2025-12-29"), ts("2026-02-02"))

    assert seen["url"].path.endswith("/datasets/WINDFOR/stream")
    assert seen["url"].params["publishDateTimeFrom"] == "2025-12-29T00:00:00Z"
    assert list(df.columns) == ["publishTime", "startTime", "generation"]
    assert len(df) == 1
    assert df.iloc[0]["startTime"] == ts("2026-01-15 12:00")
    assert df["generation"].dtype == float


def test_fetch_wind_actuals_keeps_only_wind():
    def handler(request: httpx.Request):
        assert request.url.params["fuelType"] == "WIND"
        return httpx.Response(
            200,
            json=[
                {"startTime": "2026-01-15T12:00:00Z", "fuelType": "WIND", "generation": 9742},
                {"startTime": "2026-01-15T12:00:00Z", "fuelType": "CCGT", "generation": 1},
            ],
        )

    df = client_with(handler).wind_actuals(pd.Timestamp("2026-01-02").date(), pd.Timestamp("2026-02-01").date())
    assert list(df.columns) == ["startTime", "generation"]
    assert df["generation"].tolist() == [9742.0]


def test_http_errors_raise():
    import pytest

    c = client_with(lambda r: httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        c.wind_actuals(pd.Timestamp("2026-01-02").date(), pd.Timestamp("2026-01-03").date())
