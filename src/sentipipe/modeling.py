from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from sentipipe.features import FEATURE_COLUMNS


@dataclass(frozen=True)
class Prediction:
    current_price: float
    predicted_price: float
    predicted_return: float
    direction: str
    mae: float | None
    rmse: float | None
    directional_accuracy: float | None
    validation_samples: int
    sentiment_coverage_bars: int
    sentiment_training_samples: int
    training_mode: str
    validation_status: str
    model: HistGradientBoostingRegressor


def _new_model() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(
        max_iter=150,
        learning_rate=0.06,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        random_state=17,
    )


def predict_next_bar(frame: pd.DataFrame, validation_splits: int = 5) -> Prediction:
    usable = frame.dropna(subset=FEATURE_COLUMNS + ["target_return"])
    if len(usable) < max(30, validation_splits + 5):
        raise ValueError(
            f"Need at least {max(30, validation_splits + 5)} aligned bars for prediction; "
            f"found {len(usable)}"
        )

    covered_mask = (
        usable["social_mentions"].fillna(0).gt(0)
        | usable["news_mentions"].fillna(0).gt(0)
    )
    covered = usable.loc[covered_mask]
    minimum_covered_bars = max(30, validation_splits + 5)
    validation_status = (
        "validated on sentiment-covered bars"
        if len(covered) >= minimum_covered_bars
        else (
            "out-of-sample sentiment validation unavailable: "
            f"{len(covered)} sentiment-covered bars; need {minimum_covered_bars}"
        )
    )

    mae: float | None = None
    rmse: float | None = None
    directional_accuracy: float | None = None
    validation_samples = 0
    if len(covered) >= minimum_covered_bars:
        x_covered = covered[FEATURE_COLUMNS].astype(float)
        y_covered = covered["target_return"].astype(float)
        actual: list[float] = []
        predicted: list[float] = []
        splitter = TimeSeriesSplit(n_splits=validation_splits)
        for train_index, test_index in splitter.split(x_covered):
            model = _new_model()
            model.fit(x_covered.iloc[train_index], y_covered.iloc[train_index])
            predicted.extend(model.predict(x_covered.iloc[test_index]).tolist())
            actual.extend(y_covered.iloc[test_index].tolist())
        actual_array = np.asarray(actual)
        predicted_array = np.asarray(predicted)
        mae = float(mean_absolute_error(actual_array, predicted_array))
        rmse = float(np.sqrt(mean_squared_error(actual_array, predicted_array)))
        directional_accuracy = float(np.mean(np.sign(actual_array) == np.sign(predicted_array)))
        validation_samples = len(actual)

    if len(covered) >= minimum_covered_bars:
        training = covered
        training_mode = "sentiment-covered history"
    else:
        training = usable
        training_mode = "price-history fallback; sentiment history is insufficient"

    model = _new_model()
    model.fit(training[FEATURE_COLUMNS].astype(float), training["target_return"].astype(float))
    latest = frame.dropna(subset=FEATURE_COLUMNS).iloc[-1:]
    predicted_return = float(model.predict(latest[FEATURE_COLUMNS].astype(float))[0])
    current_price = float(latest["close"].iloc[0])
    return Prediction(
        current_price=current_price,
        predicted_price=current_price * (1 + predicted_return),
        predicted_return=predicted_return,
        direction="up" if predicted_return > 0 else "down" if predicted_return < 0 else "flat",
        mae=mae,
        rmse=rmse,
        directional_accuracy=directional_accuracy,
        validation_samples=validation_samples,
        sentiment_coverage_bars=len(covered),
        sentiment_training_samples=len(training),
        training_mode=training_mode,
        validation_status=validation_status,
        model=model,
    )
