from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Asset:
    ticker: str
    name: str
    currency: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Exchange:
    name: str
    assets: tuple[Asset, ...]
    sources: tuple[str, ...]


@dataclass(frozen=True)
class Settings:
    lookback_days: int
    price_period: str
    price_interval: str
    output_dir: Path
    validation_splits: int


@dataclass(frozen=True)
class AppConfig:
    settings: Settings
    exchanges: tuple[Exchange, ...]
    apify_sources: dict[str, dict[str, Any]]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    if not isinstance(raw, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {config_path}")

    raw_settings = raw.get("settings", {})
    settings = Settings(
        lookback_days=int(raw_settings.get("lookback_days", 10)),
        price_period=str(raw_settings.get("price_period", "2y")),
        price_interval=str(raw_settings.get("price_interval", "1d")),
        output_dir=Path(raw_settings.get("output_dir", "output")),
        validation_splits=int(raw_settings.get("validation_splits", 5)),
    )
    if settings.lookback_days < 1:
        raise ValueError("settings.lookback_days must be at least 1")
    if settings.validation_splits < 2:
        raise ValueError("settings.validation_splits must be at least 2")

    exchanges: list[Exchange] = []
    for name, raw_exchange in raw.get("exchanges", {}).items():
        assets = tuple(
            Asset(
                ticker=str(item["ticker"]),
                name=str(item["name"]),
                currency=str(item.get("currency", "")),
                aliases=tuple(str(alias) for alias in item.get("aliases", [])),
            )
            for item in raw_exchange.get("assets", [])
        )
        sources = tuple(str(source) for source in raw_exchange.get("sources", []))
        if len(assets) != 5:
            raise ValueError(f"{name} must configure exactly 5 assets; found {len(assets)}")
        if len(set(sources)) < 2:
            raise ValueError(f"{name} must configure at least 2 distinct social sources")
        exchanges.append(Exchange(str(name), assets, sources))

    if not exchanges:
        raise ValueError("Configure at least one exchange under 'exchanges'")
    return AppConfig(
        settings=settings,
        exchanges=tuple(exchanges),
        apify_sources=raw.get("apify_sources", {}),
    )
