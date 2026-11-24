import numpy as np
import pandas as pd

from sentipipe.features import FEATURE_COLUMNS
from sentipipe.modeling import predict_next_bar


def test_prediction_uses_chronological_out_of_sample_splits():
    count = 100
    index = pd.date_range("2024-01-01", periods=count, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {column: np.linspace(0, 1, count) for column in FEATURE_COLUMNS},
        index=index,
    )
    frame["target_return"] = np.sin(np.arange(count) / 5) / 100
    frame["close"] = np.linspace(100, 120, count)
    result = predict_next_bar(frame, validation_splits=4)
    assert result.validation_samples > 0
    assert result.mae >= 0
    assert result.rmse >= 0
    assert 0 <= result.directional_accuracy <= 1
    assert result.predicted_price > 0
    assert result.validation_samples > 0
    assert result.training_mode == "sentiment-covered history"


def test_insufficient_sentiment_history_is_not_reported_as_validated():
    count = 100
    index = pd.date_range("2024-01-01", periods=count, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {column: np.linspace(0, 1, count) for column in FEATURE_COLUMNS},
        index=index,
    )
    frame["social_mentions"] = 0
    frame["news_mentions"] = 0
    frame["target_return"] = np.sin(np.arange(count) / 5) / 100
    frame["close"] = np.linspace(100, 120, count)

    result = predict_next_bar(frame, validation_splits=4)

    assert result.mae is None
    assert result.rmse is None
    assert result.directional_accuracy is None
    assert result.validation_samples == 0
    assert "validation unavailable" in result.validation_status
    assert "fallback" in result.training_mode
