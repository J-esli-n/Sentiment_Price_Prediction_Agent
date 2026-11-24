# Sentipipe

A Python pipeline that combines two Apify-backed social sources per exchange, Exa news, and adjusted Yahoo Finance bars to produce next-bar price forecasts with time-ordered out-of-sample validation and an HTML visualization.

## Defaults and requirements

The sample configuration covers five HKEX and five KRX assets. HKEX defaults to LIHKG and AAStocks; KRX defaults to Naver Finance and Daum Finance. These are source names, not bundled scrapers: Apify actors are configurable because each actor has its own input schema and site availability/permissions. Set each actor ID in `config.yaml` or with `APIFY_ACTOR_ID_LIHKG`, `APIFY_ACTOR_ID_AASTOCKS`, `APIFY_ACTOR_ID_NAVER_FINANCE`, and `APIFY_ACTOR_ID_DAUM_FINANCE`. Configure the matching actor inputs in `config.yaml`. Use actors and data only in compliance with each source's terms.

Python 3.10 or later is required. The pipeline loads credentials from `.env` first, then fills any missing values from `.env.example`; variables already set in the process environment take precedence. Actor IDs can also be supplied through these files. The sample `config.yaml` has intentionally blank actor IDs; set each selected actor ID and adjust its input mapping to that actor's documented schema. Input strings support `{ticker}`, `{name}`, `{query}`, `{since}`, and `{until}`. Actor result objects are normalized using common timestamp, text, and engagement field names. Adapt the normalizer if your actor returns different fields.

Copy `.env.template` to `.env` and put your credentials and actor IDs in `.env`. `.env` and `.env.example` are ignored by Git because they may contain real credentials; only the blank `.env.template` should be committed. If credentials have ever been pushed to a public repository, revoke and replace them.

Social and news timestamps are normalized to UTC. The default 10-day collection window is joined to daily price bars by publication date. Use `price_interval: 1h` for more granular bars where the selected price provider supports that interval. Each run appends deduplicated posts and news to `output/history/`, so sentiment coverage accumulates across runs. Historical bars with no collected coverage are not treated as observed negative sentiment. The report only shows out-of-sample sentiment metrics after at least 30 sentiment-covered bars are available; until then it clearly marks validation unavailable and labels the prediction as a price-history fallback. Validation errors and directional accuracy are reported as returns/forecast direction, not guaranteed performance.

## Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.template .env
# Add your credentials and Apify actor IDs to .env; never commit this file.
# Edit config.yaml with actor IDs and actor-specific inputs.
sentipipe --config config.yaml
```

Outputs are written to `output\report.html`, `output\predictions.csv`, and `output\predictions.json`. Collected sentiment is retained under `output\history\`; `output\forecast_history.csv` records each prediction and checks it against the next available price bar on later runs. The HTML report charts mention volume and sentiment for each exchange, and ranks assets by mentions and sentiment. Each asset row includes current price, n+1 estimate, sentiment, forecast direction, an indicative position, recent support/resistance, validation coverage, and any resolved forecast outcome.

If an individual asset fails to fetch or validate, the pipeline logs the failure and continues with the remaining assets; it returns a nonzero exit status if any assets failed. It fails the overall run if none could be analyzed.

## Model and interpretation

The target is the next configured price bar's close-to-close return. Technical features use only the current and prior bars. Social weighting uses post sentiment, engagement, and author followers; news uses Exa headlines and text. Validation uses expanding chronological folds (no random shuffle). Support/resistance are recent rolling-close extrema and are descriptive levels, not trading signals. The position text is a simple sentiment/forecast alignment heuristic and is not financial advice.

Run tests with `pytest`.

