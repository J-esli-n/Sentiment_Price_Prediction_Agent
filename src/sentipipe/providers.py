from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from sentipipe.config import AppConfig, Asset

POST_COLUMNS = ["source", "ticker", "timestamp", "text", "likes", "reposts", "views", "followers"]
NEWS_COLUMNS = ["ticker", "timestamp", "title", "text", "url"]


def load_local_env() -> None:
    """Load local credentials, preferring .env and preserving existing environment values."""
    for path in (".env", ".env.example"):
        load_dotenv(path, override=False)


def _first(item: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return default


def normalize_post(item: dict[str, Any], source: str, ticker: str) -> dict[str, Any] | None:
    text = _first(item, ("text", "content", "message", "post", "body", "title"), "")
    timestamp = _first(item, ("timestamp", "createdAt", "created_at", "date", "publishedAt"))
    if not str(text).strip() or timestamp is None:
        return None
    parsed = pd.to_datetime(timestamp, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    author = item.get("author") or item.get("user") or {}
    if not isinstance(author, dict):
        author = {}
    return {
        "source": source,
        "ticker": ticker,
        "timestamp": parsed,
        "text": str(text).strip(),
        "likes": _first(item, ("likes", "likeCount", "like_count"), 0),
        "reposts": _first(item, ("reposts", "shares", "retweets", "shareCount"), 0),
        "views": _first(item, ("views", "viewCount", "view_count"), 0),
        "followers": _first(item, ("followers", "followerCount", "followersCount"), _first(author, ("followers", "followersCount", "followerCount"), 0)),
    }


class ApifySocialProvider:
    def __init__(self, config: AppConfig, token: str | None = None):
        load_local_env()
        api_token = token or os.getenv("APIFY_API_TOKEN")
        if not api_token:
            raise RuntimeError("APIFY_API_TOKEN is required to collect social posts")
        try:
            from apify_client import ApifyClient
        except ImportError as exc:
            raise RuntimeError("Install project dependencies to use the Apify provider") from exc
        self.client = ApifyClient(api_token)
        self.config = config

    def collect(self, exchange_sources: tuple[str, ...], asset: Asset, lookback_days: int) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=lookback_days)).isoformat()
        until = now.isoformat()
        query = " OR ".join((asset.ticker, asset.name, *asset.aliases))
        posts: list[dict[str, Any]] = []
        for source in exchange_sources:
            source_config = self.config.apify_sources.get(source, {})
            actor_id = source_config.get("actor_id") or os.getenv(
                f"APIFY_ACTOR_ID_{source.upper()}"
            )
            if not actor_id:
                raise ValueError(
                    f"Set apify_sources.{source}.actor_id in config.yaml or "
                    f"APIFY_ACTOR_ID_{source.upper()} in the environment"
                )
            template = source_config.get("input")
            if not isinstance(template, dict):
                raise ValueError(f"Set apify_sources.{source}.input as an actor input mapping")
            actor_input = _substitute(template, {
                "ticker": asset.ticker,
                "name": asset.name,
                "query": query,
                "since": since,
                "until": until,
            })
            run = self.client.actor(actor_id).call(run_input=actor_input)
            if not run:
                raise RuntimeError(f"Apify actor {actor_id} did not return a run")
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                raise RuntimeError(f"Apify actor {actor_id} run has no default dataset")
            for item in self.client.dataset(dataset_id).iterate_items():
                normalized = normalize_post(item, source, asset.ticker)
                if normalized:
                    posts.append(normalized)
        cutoff = pd.Timestamp(now - timedelta(days=lookback_days))
        return [post for post in posts if post["timestamp"] >= cutoff]


def _substitute(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, replacement in replacements.items():
            value = value.replace("{" + key + "}", replacement)
        return value
    if isinstance(value, list):
        return [_substitute(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, replacements) for key, item in value.items()}
    return value


class ExaNewsProvider:
    def __init__(self, api_key: str | None = None):
        load_local_env()
        key = api_key or os.getenv("EXA_API_KEY")
        if not key:
            raise RuntimeError("EXA_API_KEY is required to collect news")
        try:
            from exa_py import Exa
        except ImportError as exc:
            raise RuntimeError("Install project dependencies to use the Exa provider") from exc
        self.client = Exa(api_key=key)

    def collect(self, asset: Asset, lookback_days: int) -> list[dict[str, Any]]:
        response = self.client.search_and_contents(
            f"{asset.name} {asset.ticker} stock",
            category="news",
            start_published_date=(datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat(),
            num_results=25,
            text={"max_characters": 3000},
        )
        records: list[dict[str, Any]] = []
        for result in response.results:
            published = getattr(result, "published_date", None)
            timestamp = pd.to_datetime(published, utc=True, errors="coerce")
            if pd.isna(timestamp):
                continue
            records.append({
                "ticker": asset.ticker,
                "timestamp": timestamp,
                "title": getattr(result, "title", "") or "",
                "text": getattr(result, "text", "") or "",
                "url": getattr(result, "url", "") or "",
            })
        return records


def fetch_prices(asset: Asset, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Install project dependencies to fetch prices") from exc
    frame = yf.download(asset.ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if frame.empty:
        raise RuntimeError(f"No price data returned for {asset.ticker}")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame.rename(columns={"Close": "close", "Volume": "volume"})
    required = {"close", "volume"}
    if not required.issubset(frame.columns):
        raise RuntimeError(f"Price data for {asset.ticker} is missing {required - set(frame.columns)}")
    return frame[["close", "volume"]].dropna().sort_index()
