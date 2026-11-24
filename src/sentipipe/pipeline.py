from __future__ import annotations

from typing import Any

import pandas as pd

from sentipipe.config import AppConfig, Asset
from sentipipe.features import build_feature_frame, support_resistance
from sentipipe.history import (
    NEWS_COLUMNS,
    SOCIAL_COLUMNS,
    asset_history_path,
    update_forecast_history,
    update_record_history,
)
from sentipipe.modeling import predict_next_bar
from sentipipe.providers import ApifySocialProvider, ExaNewsProvider, fetch_prices
from sentipipe.report import write_report


def _position(sentiment: float, predicted_return: float) -> str:
    if sentiment > 0.15 and predicted_return > 0:
        return "bullish bias; consider long only with risk controls"
    if sentiment < -0.15 and predicted_return < 0:
        return "bearish bias; consider defensive/short exposure only if permitted"
    return "neutral; wait for confirmation"


def analyze_asset(
    exchange_name: str,
    sources: tuple[str, ...],
    asset: Asset,
    config: AppConfig,
    social_provider: Any,
    news_provider: Any,
    price_fetcher: Any = fetch_prices,
) -> dict[str, Any]:
    prices = price_fetcher(asset, config.settings.price_period, config.settings.price_interval)
    posts = update_record_history(
        asset_history_path(config.settings.output_dir, exchange_name, asset.ticker, "social"),
        social_provider.collect(sources, asset, config.settings.lookback_days),
        SOCIAL_COLUMNS,
        ["source", "ticker", "timestamp", "text"],
    )
    news = update_record_history(
        asset_history_path(config.settings.output_dir, exchange_name, asset.ticker, "news"),
        news_provider.collect(asset, config.settings.lookback_days),
        NEWS_COLUMNS,
        ["ticker", "timestamp", "title", "url"],
    )
    features = build_feature_frame(prices, posts, news, config.settings.price_interval)
    prediction = predict_next_bar(features, config.settings.validation_splits)
    latest = features.iloc[-1]
    support, resistance = support_resistance(prices)
    current_price = prediction.current_price
    latest_news = news.sort_values("timestamp").iloc[-1] if not news.empty else None
    source_names = sorted(posts["source"].dropna().astype(str).unique()) if "source" in posts else []
    outcome = update_forecast_history(
        config.settings.output_dir / "forecast_history.csv",
        {
            "exchange": exchange_name,
            "ticker": asset.ticker,
            "origin_timestamp": prices.index[-1],
            "current_price": current_price,
            "predicted_price": prediction.predicted_price,
            "predicted_return": prediction.predicted_return,
            "direction": prediction.direction,
        },
        prices,
    )
    return {
        "exchange": exchange_name,
        "ticker": asset.ticker,
        "asset_name": asset.name,
        "currency": asset.currency,
        "current_price": current_price,
        "predicted_next_price": prediction.predicted_price,
        "predicted_return_pct": prediction.predicted_return * 100,
        "direction": prediction.direction,
        "position": _position(float(latest["social_sentiment"]), prediction.predicted_return),
        "social_mentions": int(latest["social_mentions"]),
        "social_sentiment": float(latest["social_sentiment"]),
        "news_mentions": int(latest["news_mentions"]),
        "news_sentiment": float(latest["news_sentiment"]),
        "social_sources": int(latest["social_sources"]),
        "social_sources_used": ", ".join(source_names),
        "recent_news_title": str(latest_news["title"]) if latest_news is not None else "",
        "recent_news_url": str(latest_news["url"]) if latest_news is not None else "",
        "support": support,
        "resistance": resistance,
        "oos_mae_return": prediction.mae,
        "oos_rmse_return": prediction.rmse,
        "oos_directional_accuracy": prediction.directional_accuracy,
        "oos_validation_samples": prediction.validation_samples,
        "oos_validation_status": prediction.validation_status,
        "sentiment_coverage_bars": prediction.sentiment_coverage_bars,
        "sentiment_training_samples": prediction.sentiment_training_samples,
        "training_mode": prediction.training_mode,
        **outcome,
        "bar_interval": config.settings.price_interval,
    }


def run_pipeline(config: AppConfig) -> tuple[Any, Any]:
    social_provider = ApifySocialProvider(config)
    news_provider = ExaNewsProvider()
    rows = []
    failures: list[str] = []
    for exchange in config.exchanges:
        for asset in exchange.assets:
            try:
                rows.append(analyze_asset(
                    exchange.name, exchange.sources, asset, config,
                    social_provider, news_provider,
                ))
            except Exception as exc:
                failures.append(f"{exchange.name}/{asset.ticker}: {exc}")
    if not rows:
        raise RuntimeError("No assets were successfully analyzed. " + "; ".join(failures))
    paths = write_report(rows, config.settings.output_dir)
    return paths, failures
