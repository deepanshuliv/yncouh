# Design decisions and research

Each decision below lists the options considered, the evidence, and the choice.
Numbers come from `python -m scripts.compare_approaches` on the cached January
2026 data (full output: [approach-comparison.txt](approach-comparison.txt)).

## 1. Scope: which days are analysed

"Purchase decisions made in January 2026" means decision days 1–31 Jan. Each
decision buys power for the next day, so **delivery days are 2 Jan – 1 Feb 2026**
(31 days, 1,488 half-hours, all present in FUELHH).

Forecasts are fetched by `publishTime` from **29 Dec 2025 to 2 Feb 2026**. The
forecast for 2 Jan is published on 1 Jan, and the horizon analysis needs runs up
to ~45 h before the first delivery slot.

The other reading (delivery during January) would shift the window by one day; the
dates live in `backend/app/data.py` and can be changed in one place.

## 2. Decision time (cutoff)

The trader must submit bids before the GB day-ahead auction closes:

| Auction | Gate closure (UK time) | Source |
|---|---|---|
| EPEX SPOT GB day-ahead (hourly) | 09:20 | [S&P Global note](https://www.spglobal.com/commodity-insights/en/pricing-benchmarks/our-methodology/subscriber-notes/120920-platts-to-amend-uk-day-ahead-power-assessments-timing-from-jan-4) (secondary source) |
| Nord Pool N2EX day-ahead | 09:50 | [Nord Pool](https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-n2ex-day-ahead-auction) |

WINDFOR runs are published at 02:30, 04:30, 07:30, **09:30**, 11:30, 15:30, 18:30
and 22:30 UTC (= UK time in January), so the choice of cutoff decides which run
the trader sees:

| Cutoff | Run used | MAE (MW) | Bias (MW) |
|---|---|---|---|
| 09:00 | 07:30 | 2023 | +1744 |
| **09:20** (EPEX) | 07:30 | 2023 | +1744 |
| 09:50 (N2EX) | 09:30 | 1996 | +1727 |

**Decision: default 09:20**, the earlier of the two closes; any bid must be in by
then. 09:50 is offered as a one-click preset, and any half-hour can be chosen.
Waiting for the 09:30 run improves MAE by only 27 MW.

Rule: for a slot on UK delivery day D, use the **latest forecast with
`publishTime <= D-1 at the cutoff (UK time)`**. `<=` because a run published at
the cutoff is available. Delivery day is the UK local date. Clock-change days are
handled (non-existent times shift forward, repeated times use the first
occurrence) and are covered by tests.

## 3. Selecting the forecast: four implementations, one test suite

| Approach | Time (ms) | Same as reference | Slots using future forecasts | MAE (MW) |
|---|---|---|---|---|
| `naive_latest` (newest forecast, ignores cutoff) | 0.8 | no | 1,734 | **1652** |
| `python_loop` (reference) | 42 | yes | 0 | 2023 |
| **`filter_sort`** | 3.5 | yes | 0 | 2023 |
| `merge_asof` | 2.3 | yes | 0 | 2023 |

The naive version looks ~18% more accurate because it peeks at forecasts made
after the decision: exactly the mistake the dashboard must avoid. The test suite
proves it leaks.

**Decision: `filter_sort`.** Correct, easiest to read ("drop what was published
too late, keep the newest"), and fast enough. Results are cached per cutoff, so
the 1 ms gap to `merge_asof` is irrelevant.

## 4. Hourly forecasts vs half-hourly actuals

WINDFOR is hourly; FUELHH is half-hourly. Options, scored only on the :30 slots
(the only place they differ):

| Method | :30 slots | MAE | Bias-removed std |
|---|---|---|---|
| `hourly` (compare on the hour only) | 0 (half the data unused) | – | – |
| `hold` (xx:30 = xx:00) | 744 | 2061 | 1814 |
| **`linear`** (midpoint of xx:00 and next hour) | 744 | **2024** | **1791** |

**Decision: linear**, interpolated only within one forecast run and only between
two consecutive hours (never across runs, never extrapolated).

Assumption: a WINDFOR value is treated as the expected output at that hour. Elexon
does not say clearly whether it is a point value or an hourly average; if it were
an hourly average, `hold` would be the natural choice. The data favours linear
either way.

## 5. Metrics

Error = **forecast − actual** (positive = forecast too high = wind came in short).

| Metric | Why |
|---|---|
| MAE | Typical miss in MW; easy to explain |
| RMSE | Penalises large misses, which hurt most |
| Bias | Mean signed error: systematically high or low? |
| Error spread (std) | Error left once the bias is corrected |
| nMAE % | MAE as % of mean actual. Per-slot % error is avoided because it blows up at low wind. |
| P90 shortfall (raw and bias-corrected) | How much to hold in reserve to cover wind shortfall in 90% of half-hours |
| Max error | Worst case |

## 6. The +1.7 GW bias

The forecast available at decision time averaged **+1.74 GW (15%) above** metered
wind output. Checks:

- Forecasts made only 0–3 h ahead are still **+1.43 GW** high, so it is not mainly
  lead-time weather uncertainty.
- The bias is larger at high wind (about +0.8 GW when actual is 4–12 GW, about
  +2.1 GW when actual is above 12 GW).
- WINDFOR covers wind farms "visible to the ESO with operational metering"
  ([BMRS WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR),
  [Elexon glossary](https://www.elexon.co.uk/bsc/glossary/wind-generation-forecast/)),
  broadly the same metered set as FUELHH WIND, so a coverage mismatch is unlikely
  to be the main cause.

**Interpretation (not verified):** consistent with curtailment. FUELHH is metered
output after balancing actions (wind farms paid to reduce output when the network
is constrained), while the forecast appears to describe what the wind could
produce. The dashboard therefore says "likely" and reports the bias-corrected
spread (1.79 GW) separately, because a systematic offset can be corrected for.

## 7. Horizon chart limited to 45 h

Each run covers 73 hourly slots, so beyond ~45 h ahead only some of the eight daily
runs reach a given slot (bucket counts fall from 1,488 to 31). Those buckets mix
different run times and are not comparable, so the chart stops at 45 h.

## 8. Architecture

- **Data is cached** in `backend/data/*.csv` (about 1 MB) instead of calling Elexon
  on every page load: fast, reproducible, and the demo cannot break if the API is
  down. `scripts/fetch_data.py` refreshes it.
- **Pure functions, thin API.** `selection`, `alignment`, `metrics` and `analysis`
  are pandas functions with no I/O, unit-tested directly. `main.py` only validates
  input, caches per cutoff (`lru_cache`) and shapes JSON.
- **One container.** FastAPI serves both `/api/*` and the built React app, so
  there is one image and one URL and no CORS configuration.
- **Deployment: Heroku container stack** (`heroku.yml`). Vercel does not run
  Docker images, and pandas strains its Python function size limits.
