import math

import numpy as np
import pytest

from app.metrics import error_metrics

# Sign convention: error = forecast - actual (positive = forecast too high).


def test_known_values():
    m = error_metrics(forecast=[110, 90, 130], actual=[100, 100, 100])
    # errors: +10, -10, +30
    assert m["count"] == 3
    assert m["bias"] == pytest.approx(10.0)
    assert m["mae"] == pytest.approx(50 / 3)
    assert m["rmse"] == pytest.approx(math.sqrt((100 + 100 + 900) / 3))
    assert m["max_abs_error"] == pytest.approx(30)
    assert m["nmae_pct"] == pytest.approx(100 * (50 / 3) / 100)


def test_error_std_is_spread_after_removing_bias():
    # errors +10, -10, +30: mean 10, deviations 0, -20, +20
    m = error_metrics(forecast=[110, 90, 130], actual=[100, 100, 100])
    assert m["error_std"] == pytest.approx(math.sqrt(800 / 3))
    # A constant offset is pure bias: no spread left.
    assert error_metrics([150, 250], [100, 200])["error_std"] == pytest.approx(0)


def test_overforecast_gives_positive_bias():
    assert error_metrics([120, 120], [100, 100])["bias"] > 0
    assert error_metrics([80, 80], [100, 100])["bias"] < 0


def test_rmse_is_never_below_mae():
    rng = np.random.default_rng(0)
    actual = rng.uniform(1000, 15000, 500)
    forecast = actual + rng.normal(0, 1500, 500)
    m = error_metrics(forecast, actual)
    assert m["rmse"] >= m["mae"]


def test_p90_abs_error():
    m = error_metrics(forecast=list(range(1, 11)), actual=[0] * 10)
    assert m["p90_abs_error"] == pytest.approx(np.percentile(range(1, 11), 90))


def test_shortfall_p90_covers_wind_coming_in_below_forecast():
    # Wind fell short of forecast by 0..900 MW; a 90% reserve needs ~810 MW.
    actual = [1000 - s for s in range(0, 1000, 100)]
    m = error_metrics(forecast=[1000] * 10, actual=actual)
    assert m["shortfall_p90"] == pytest.approx(np.percentile(range(0, 1000, 100), 90))


def test_bias_corrected_shortfall_removes_the_average_offset():
    # Shortfalls 0..900 (mean 450). Once the 450 MW bias is corrected for,
    # the leftover shortfalls are -450..450 and the 90% reserve is 360 MW.
    actual = [1000 - s for s in range(0, 1000, 100)]
    m = error_metrics(forecast=[1000] * 10, actual=actual)
    assert m["shortfall_p90_debiased"] == pytest.approx(360)


def test_shortfall_p90_is_zero_when_forecast_always_low():
    assert error_metrics([50, 60], [100, 100])["shortfall_p90"] == 0


def test_missing_values_are_ignored():
    m = error_metrics([110, np.nan, 90], [100, 100, np.nan])
    assert m["count"] == 1
    assert m["mae"] == pytest.approx(10)


def test_empty_input_returns_nulls():
    m = error_metrics([], [])
    assert m["count"] == 0
    assert m["mae"] is None and m["rmse"] is None and m["bias"] is None


def test_results_are_plain_floats_for_json():
    m = error_metrics([110], [100])
    assert all(v is None or type(v) in (int, float) for v in m.values())
