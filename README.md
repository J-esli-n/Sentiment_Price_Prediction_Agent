# Sentipipe

Sentipipe is a Python pipeline for forecasting the next price bar using social sentiment, news, and historical market data.

## Defaults and requirements

- **Supported Python:** 3.10 or later.
- **Default assets:** five HKEX and five KRX assets, configured in `config.yaml`.
- **Social sources:** configurable Apify actors. The sample sources are LIHKG and AAStocks for HKEX, and Naver Finance and Daum Finance for KRX.
- **Actor configuration:**
  - Set actor IDs in `config.yaml` or with `APIFY_ACTOR_ID_LIHKG`, `APIFY_ACTOR_ID_AASTOCKS`, `APIFY_ACTOR_ID_NAVER_FINANCE`, and `APIFY_ACTOR_ID_DAUM_FINANCE`.
  - Configure each actor's input mapping to match its documented schema.
  - Input strings support `{ticker}`, `{name}`, `{query}`, `{since}`, and `{until}`.
  - Actor results are normalized using common timestamp, text, and engagement field names. Adapt the normalizer if your actor uses different fields.
  - Use actors and data in compliance with each source's terms.
- **Credentials:**
  - Copy `.env.template` to `.env` and add your credentials and actor IDs.
  - `.env` and `.env.example` are ignored by Git because they may contain secrets. Commit only the blank `.env.template`.
  - Environment variables already set in the process take precedence; the pipeline also loads `.env` and fills missing values from `.env.example`.
  - Revoke and replace credentials if they have been exposed publicly.
- **Data handling and validation:**
  - Social and news timestamps are normalized to UTC.
  - The default 10-day collection window is joined to daily price bars by publication date. Set `price_interval: 1h` for more granular bars if supported by the selected provider.
  - Posts and news are deduplicated and appended to `output/history/` across runs.
  - Price bars without collected sentiment are not treated as observed negative sentiment.
  - Out-of-sample sentiment metrics are reported only after at least 30 sentiment-covered bars are available. Otherwise, validation is marked unavailable and the prediction uses a price-history fallback.
  - Validation errors and directional accuracy describe returns and forecast direction; they do not guarantee performance.

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

- **Generated files:**
  - `output\report.html` — interactive HTML report.
  - `output\predictions.csv` and `output\predictions.json` — prediction results.
  - `output\history\` — deduplicated social and news history.
  - `output\forecast_history.csv` — forecasts and outcomes resolved against later price bars.
- The HTML report charts mentions and sentiment by exchange and ranks assets by mentions and sentiment.
- Each asset row includes its current price, next-bar estimate, sentiment, forecast direction, indicative position, recent support/resistance, validation coverage, and any resolved forecast outcome.
- If an asset fails to fetch or validate, the pipeline logs the failure and continues with other assets.
- The command exits with a nonzero status if any assets failed, or if no assets could be analyzed.

## Model and interpretation

- **Prediction target:** the next configured price bar's close-to-close return.
- **Technical features:** use only the current and prior bars.
- **Social features:** use post sentiment, engagement, and author followers.
- **News features:** use Exa headlines and text.
- **Validation:** expanding chronological folds; data is not randomly shuffled.
- **Support and resistance:** recent rolling-close extrema, provided as descriptive levels rather than trading signals.
- **Position text:** a simple sentiment/forecast alignment heuristic, not financial advice.
- **Tests:** run with `pytest`.

