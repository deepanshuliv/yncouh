"""Compare forecast-selection and alignment approaches on the real January data.

Usage (from backend/):  python -m scripts.compare_approaches
"""

import time as clock
from datetime import time

import pandas as pd

from app.alignment import ALIGNMENTS
from app.analysis import in_window, join_actuals
from app.data import load_dataset
from app.metrics import error_metrics
from app.selection import APPROACHES, decision_cutoffs

CUTOFF = time(9, 20)  # EPEX SPOT GB gate closure


def timed(fn, *args, repeat=5):
    best = float("inf")
    for _ in range(repeat):
        start = clock.perf_counter()
        out = fn(*args)
        best = min(best, clock.perf_counter() - start)
    return out, best


def main() -> None:
    data = load_dataset()
    forecasts = ALIGNMENTS["linear"](data.forecasts)
    print(f"Forecast rows (after half-hour alignment): {len(forecasts):,}\n")

    print("== Forecast selection (cutoff 09:20 UK on D-1) ==")
    reference, _ = timed(APPROACHES["python_loop"], forecasts, CUTOFF, repeat=1)
    deadlines = decision_cutoffs(forecasts["startTime"], CUTOFF)
    print(f"{'approach':<14}{'time (ms)':>11}{'matches ref':>13}{'leaks future':>14}{'MAE (MW)':>10}")
    for name, fn in APPROACHES.items():
        out, secs = timed(fn, forecasts, CUTOFF, repeat=1 if name == "python_loop" else 5)
        same = out.reset_index(drop=True).equals(reference.reset_index(drop=True))
        merged = out.merge(
            pd.DataFrame({"startTime": forecasts["startTime"], "deadline": deadlines}).drop_duplicates(),
            on="startTime",
        )
        leaks = int((merged["publishTime"] > merged["deadline"]).sum())
        pairs = in_window(join_actuals(out, data.actuals), data.first_day, data.last_day)
        mae = error_metrics(pairs["forecast"], pairs["actual"])["mae"]
        print(f"{name:<14}{secs * 1000:>11.1f}{str(same):>13}{leaks:>14,}{mae:>10.0f}")

    print("\n== Hourly -> half-hourly alignment (filter_sort, cutoff 09:20) ==")
    print("Only :30 slots differ between methods, so they are scored on those alone.")
    print(f"{'method':<10}{'slots':>7}{'MAE':>8}{'RMSE':>8}{'bias':>8}{'err std':>9}")
    for name, align in ALIGNMENTS.items():
        chosen = APPROACHES["filter_sort"](align(data.forecasts), CUTOFF)
        pairs = in_window(join_actuals(chosen, data.actuals), data.first_day, data.last_day)
        pairs = pairs[pairs["startTime"].dt.minute == 30]
        if pairs.empty:
            print(f"{name:<10}{0:>7}   (no :30 values - half the slots go unscored)")
            continue
        m = error_metrics(pairs["forecast"], pairs["actual"])
        print(
            f"{name:<10}{m['count']:>7}{m['mae']:>8.0f}{m['rmse']:>8.0f}"
            f"{m['bias']:>8.0f}{m['error_std']:>9.0f}"
        )

    print("\n== Sensitivity to the decision cutoff (linear, filter_sort) ==")
    print(f"{'cutoff':<8}{'run used (UTC)':<16}{'MAE':>8}{'bias':>8}{'err std':>9}")
    aligned = ALIGNMENTS["linear"](data.forecasts)
    for hh, mm in [(7, 0), (9, 0), (9, 20), (9, 50), (11, 0), (12, 0)]:
        chosen = APPROACHES["filter_sort"](aligned, time(hh, mm))
        pairs = in_window(join_actuals(chosen, data.actuals), data.first_day, data.last_day)
        runs = ", ".join(sorted(pairs["publishTime"].dt.strftime("%H:%M").unique()))
        m = error_metrics(pairs["forecast"], pairs["actual"])
        print(f"{hh:02d}:{mm:02d}   {runs:<16}{m['mae']:>8.0f}{m['bias']:>8.0f}{m['error_std']:>9.0f}")

if __name__ == "__main__":
    main()
