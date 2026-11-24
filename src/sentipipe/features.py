from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_ANALYZER = SentimentIntensityAnalyzer()
SOCIAL_FEATURES = ["social_sentiment", "social_mentions", "social_engagement", "social_sources"]
NEWS_FEATURES = ["news_sentiment", "news_mentions"]
FEATURE_COLUMNS = [
    "return_1", "return_5", "volatility_5", "volume_change", "sma_gap",
    *SOCIAL_FEATURES, *NEWS_FEATURES,
]


def sentiment_score(text: str) -> float:
    return float(_ANALYZER.polarity_scores(text)["compound"])


def _number(value: Any) -> float:
    try:
        number = float(value)
        return number if np.isfinite(number) and number >= 0 else 0.0
    except (TypeError, ValueError):
        return 0.0


def aggregate_social(posts: pd.DataFrame, interval: str = "1D") -> pd.DataFrame:
    if posts.empty:
        return pd.DataFrame(columns=SOCIAL_FEATURES, index=pd.DatetimeIndex([], tz="UTC"))
    frame = posts.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"])
    if frame.empty:
        return pd.DataFrame(columns=SOCIAL_FEATURES, index=pd.DatetimeIndex([], tz="UTC"))
    frame["score"] = frame["text"].fillna("").map(sentiment_score)
    for column in ("likes", "reposts", "views", "followers"):
        frame[column] = frame[column].map(_number) if column in frame else 0.0
    frame["engagement"] = frame["likes"] + frame["reposts"] + frame["views"]
    frame["weight"] = np.log1p(frame["engagement"]) + np.log1p(frame["followers"])
    frame["weighted_score"] = frame["score"] * (frame["weight"] + 1.0)
    frame["bucket"] = frame["timestamp"].dt.floor(interval)
    grouped = frame.groupby("bucket", sort=True).agg(
        weighted_score=("weighted_score", "sum"),
        weight=("weight", "sum"),
        social_mentions=("text", "size"),
        social_engagement=("engagement", "sum"),
        social_sources=("source", "nunique"),
    )
    grouped["social_sentiment"] = grouped["weighted_score"] / (grouped["weight"] + grouped["social_mentions"])
    return grouped[SOCIAL_FEATURES].rename_axis("timestamp")


def aggregate_news(news: pd.DataFrame, interval: str = "1D") -> pd.DataFrame:
    if news.empty:
        return pd.DataFrame(columns=NEWS_FEATURES, index=pd.DatetimeIndex([], tz="UTC"))
    frame = news.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"])
    if frame.empty:
        return pd.DataFrame(columns=NEWS_FEATURES, index=pd.DatetimeIndex([], tz="UTC"))
    frame["score"] = (frame["title"].fillna("") + ". " + frame["text"].fillna("")).map(sentiment_score)
    frame["bucket"] = frame["timestamp"].dt.floor(interval)
    grouped = frame.groupby("bucket", sort=True).agg(
        news_sentiment=("score", "mean"),
        news_mentions=("score", "size"),
    )
    return grouped[NEWS_FEATURES].rename_axis("timestamp")


def build_feature_frame(
    prices: pd.DataFrame,
    posts: pd.DataFrame,
    news: pd.DataFrame,
    interval: str = "1D",
) -> pd.DataFrame:
    frame = prices.copy().sort_index()
    frame.index = pd.to_datetime(frame.index, utc=True)
    close = pd.to_numeric(frame["close"], errors="coerce")
    volume = pd.to_numeric(frame["volume"], errors="coerce")
    frame["return_1"] = close.pct_change()
    frame["return_5"] = close.pct_change(5)
    frame["volatility_5"] = frame["return_1"].rolling(5, min_periods=3).std()
    frame["volume_change"] = volume.pct_change().replace([np.inf, -np.inf], np.nan)
    frame["sma_gap"] = close / close.rolling(20, min_periods=5).mean() - 1
    for signals in (aggregate_social(posts, interval), aggregate_news(news, interval)):
        if not signals.empty:
            signals.index = pd.to_datetime(signals.index, utc=True)
            frame = frame.join(signals, how="left")
    for column in (*SOCIAL_FEATURES, *NEWS_FEATURES):
        if column not in frame:
            frame[column] = 0.0
    frame[["social_mentions", "social_engagement", "social_sources", "news_mentions"]] = frame[
        ["social_mentions", "social_engagement", "social_sources", "news_mentions"]
    ].fillna(0.0)
    # Signals are only joined to the bar on or after publication; never backfill future data.
    frame[["social_sentiment", "news_sentiment"]] = frame[
        ["social_sentiment", "news_sentiment"]
    ].fillna(0.0)
    frame["target_return"] = close.shift(-1) / close - 1
    return frame.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURE_COLUMNS)


def support_resistance(prices: pd.DataFrame, window: int = 20) -> tuple[float | None, float | None]:
    closes = pd.to_numeric(prices["close"], errors="coerce").dropna().tail(window)
    if closes.empty:
        return None, None
    current = float(closes.iloc[-1])
    below = closes[closes < current]
    above = closes[closes > current]
    return (
        float(below.max()) if not below.empty else None,
        float(above.min()) if not above.empty else None,
    )
