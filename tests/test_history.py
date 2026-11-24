import pandas as pd

from sentipipe.history import update_forecast_history, update_record_history


def test_record_history_deduplicates_and_keeps_latest_engagement(tmp_path):
    path = tmp_path / "history.csv"
    original = {
        "source": "forum",
        "ticker": "0700.HK",
        "timestamp": "2025-01-01T10:00:00Z",
        "text": "Positive outlook",
        "likes": 2,
        "reposts": 0,
        "views": 10,
        "followers": 5,
    }
    columns = list(original)

    update_record_history(path, [original], columns, ["source", "ticker", "timestamp", "text"])
    updated = {**original, "likes": 5}
    result = update_record_history(path, [updated], columns, ["source", "ticker", "timestamp", "text"])

    assert len(result) == 1
    assert result.iloc[0]["likes"] == 5


def test_forecast_is_resolved_against_next_available_bar(tmp_path):
    path = tmp_path / "forecast_history.csv"
    origin = pd.Timestamp("2025-01-01", tz="UTC")
    first_prices = pd.DataFrame(
        {"close": [100.0]},
        index=pd.DatetimeIndex([origin]),
    )
    forecast = {
        "exchange": "HKEX",
        "ticker": "0700.HK",
        "origin_timestamp": origin,
        "current_price": 100.0,
        "predicted_price": 103.0,
        "predicted_return": 0.03,
        "direction": "up",
    }

    pending = update_forecast_history(path, forecast, first_prices)
    assert pending["pending_forecast_count"] == 1
    assert pending["realized_forecast_count"] == 0

    next_prices = pd.DataFrame(
        {"close": [100.0, 102.0]},
        index=pd.DatetimeIndex([origin, origin + pd.Timedelta(days=1)]),
    )
    resolved = update_forecast_history(path, forecast, next_prices)

    assert resolved["pending_forecast_count"] == 1
    assert resolved["realized_forecast_count"] == 1
    assert resolved["last_actual_price"] == 102.0
    assert resolved["last_forecast_absolute_error"] == 1.0
    assert resolved["last_forecast_direction_correct"] is True
