from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

SOCIAL_COLUMNS = [
    "source", "ticker", "timestamp", "text", "likes", "reposts", "views", "followers",
]
NEWS_COLUMNS = ["ticker", "timestamp", "title", "text", "url"]
FORECAST_COLUMNS = [
    "exchange", "ticker", "origin_timestamp", "current_price", "predicted_price",
    "predicted_return", "direction", "actual_timestamp", "actual_price",
    "actual_return", "absolute_error", "direction_correct",
]


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_").lower()


def asset_history_path(output_dir: Path, exchange: str, ticker: str, kind: str) -> Path:
    return output_dir / "history" / f"{_slug(exchange)}-{_slug(ticker)}-{kind}.csv"


def update_record_history(
    path: Path,
    records: list[dict[str, Any]],
    columns: list[str],
    key_columns: list[str],
) -> pd.DataFrame:
    incoming = pd.DataFrame(records, columns=columns)
    if path.exists():
        existing = pd.read_csv(path)
        missing = set(columns) - set(existing.columns)
        if missing:
            raise ValueError(f"History file {path} is missing columns: {sorted(missing)}")
        existing = existing[columns]
    else:
        existing = pd.DataFrame(columns=columns)

    combined = pd.concat([existing, incoming], ignore_index=True)
    if combined.empty:
        return combined
    combined["timestamp"] = pd.to_datetime(
        combined["timestamp"], utc=True, errors="raise", format="mixed"
    )
    combined = combined.drop_duplicates(subset=key_columns, keep="last")
    combined = combined.sort_values("timestamp").reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False)
    return combined


def update_forecast_history(
    path: Path,
    forecast: dict[str, Any],
    prices: pd.DataFrame,
) -> dict[str, Any]:
    if path.exists():
        history = pd.read_csv(path)
        missing = set(FORECAST_COLUMNS) - set(history.columns)
        if missing:
            raise ValueError(f"Forecast history {path} is missing columns: {sorted(missing)}")
        history = history[FORECAST_COLUMNS]
    else:
        history = pd.DataFrame(columns=FORECAST_COLUMNS)

    if not history.empty:
        history["origin_timestamp"] = pd.to_datetime(
            history["origin_timestamp"], utc=True, errors="raise"
        )
        history["actual_timestamp"] = pd.to_datetime(
            history["actual_timestamp"], utc=True, errors="coerce"
        )
        history["direction_correct"] = history["direction_correct"].astype("object")

    price_bars = prices.copy()
    price_bars.index = pd.to_datetime(price_bars.index, utc=True)
    price_bars = price_bars.sort_index()
    asset_rows = history[
        (history["exchange"] == forecast["exchange"])
        & (history["ticker"] == forecast["ticker"])
    ] if not history.empty else history

    for row_index, row in asset_rows.iterrows():
        if pd.notna(row["actual_timestamp"]):
            continue
        future_bars = price_bars.loc[price_bars.index > row["origin_timestamp"], "close"]
        if future_bars.empty:
            continue
        actual_timestamp = future_bars.index[0]
        actual_price = float(future_bars.iloc[0])
        actual_return = actual_price / float(row["current_price"]) - 1
        actual_direction = "up" if actual_return > 0 else "down" if actual_return < 0 else "flat"
        history.loc[row_index, "actual_timestamp"] = actual_timestamp
        history.loc[row_index, "actual_price"] = actual_price
        history.loc[row_index, "actual_return"] = actual_return
        history.loc[row_index, "absolute_error"] = abs(actual_price - float(row["predicted_price"]))
        history.loc[row_index, "direction_correct"] = row["direction"] == actual_direction

    origin_timestamp = pd.to_datetime(forecast["origin_timestamp"], utc=True)
    same_pending = (
        (history["exchange"] == forecast["exchange"])
        & (history["ticker"] == forecast["ticker"])
        & (history["origin_timestamp"] == origin_timestamp)
        & history["actual_timestamp"].isna()
    ) if not history.empty else pd.Series(dtype=bool)
    if not history.empty and same_pending.any():
        history = history.loc[~same_pending]

    new_forecast = {column: forecast.get(column) for column in FORECAST_COLUMNS}
    new_forecast["origin_timestamp"] = origin_timestamp
    new_forecast["actual_timestamp"] = pd.NaT
    new_forecast["actual_price"] = float("nan")
    new_forecast["actual_return"] = float("nan")
    new_forecast["absolute_error"] = float("nan")
    new_forecast["direction_correct"] = None
    if history.empty:
        history = pd.DataFrame([new_forecast], columns=FORECAST_COLUMNS)
    else:
        history = pd.concat([history, pd.DataFrame([new_forecast])], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False)

    asset_rows = history[
        (history["exchange"] == forecast["exchange"])
        & (history["ticker"] == forecast["ticker"])
    ]
    resolved = asset_rows[asset_rows["actual_timestamp"].notna()]
    latest = resolved.sort_values("actual_timestamp").iloc[-1] if not resolved.empty else None
    return {
        "realized_forecast_count": int(len(resolved)),
        "pending_forecast_count": int(asset_rows["actual_timestamp"].isna().sum()),
        "last_actual_timestamp": latest["actual_timestamp"] if latest is not None else None,
        "last_actual_price": float(latest["actual_price"]) if latest is not None else None,
        "last_forecast_absolute_error": (
            float(latest["absolute_error"]) if latest is not None else None
        ),
        "last_forecast_direction_correct": (
            _as_bool(latest["direction_correct"]) if latest is not None else None
        ),
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1"}
