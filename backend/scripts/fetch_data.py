"""Download the January 2026 WINDFOR and FUELHH(WIND) data into backend/data.

Usage (from backend/):  python -m scripts.fetch_data
"""

from app.data import (
    ACTUALS_CSV,
    FIRST_DELIVERY_DAY,
    FORECASTS_CSV,
    FORECASTS_PUBLISHED_FROM,
    FORECASTS_PUBLISHED_TO,
    LAST_DELIVERY_DAY,
    save_dataset,
)
from app.elexon import ElexonClient


def main() -> None:
    client = ElexonClient()
    forecasts = client.wind_forecasts(FORECASTS_PUBLISHED_FROM, FORECASTS_PUBLISHED_TO)
    actuals = client.wind_actuals(FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY)
    save_dataset(forecasts, actuals)
    print(f"{len(forecasts):>6} forecast rows -> {FORECASTS_CSV}")
    print(f"{len(actuals):>6} actual rows   -> {ACTUALS_CSV}")


if __name__ == "__main__":
    main()
