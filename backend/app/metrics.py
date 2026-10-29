"""Forecast error metrics. Convention: error = forecast - actual."""

from typing import Iterable

import numpy as np


def _f(value) -> float:
    return float(value)


def error_metrics(forecast: Iterable[float], actual: Iterable[float]) -> dict:
    f = np.asarray(forecast, dtype=float)
    a = np.asarray(actual, dtype=float)
    ok = ~(np.isnan(f) | np.isnan(a))
    f, a = f[ok], a[ok]

    if f.size == 0:
        keys = ["mae", "rmse", "bias", "nmae_pct", "error_std", "max_abs_error", "p90_abs_error", "shortfall_p90", "shortfall_p90_debiased"]
        return {"count": 0, **{k: None for k in keys}}

    err = f - a
    abs_err = np.abs(err)
    mae = abs_err.mean()
    mean_actual = a.mean()
    return {
        "count": int(err.size),
        "mae": _f(mae),
        "rmse": _f(np.sqrt(np.mean(err**2))),
        "bias": _f(err.mean()),
        # Error left once the average bias is corrected for.
        "error_std": _f(err.std()),
        # MAE as % of mean actual output; avoids per-slot % blowing up at low wind.
        "nmae_pct": _f(100 * mae / mean_actual) if mean_actual else None,
        "max_abs_error": _f(abs_err.max()),
        "p90_abs_error": _f(np.percentile(abs_err, 90)),
        # How far wind can fall below forecast in 90% of slots: a reserve to buy.
        "shortfall_p90": _f(max(np.percentile(err, 90), 0.0)),
        # Same reserve once the average bias has been corrected for.
        "shortfall_p90_debiased": _f(max(np.percentile(err - err.mean(), 90), 0.0)),
    }
