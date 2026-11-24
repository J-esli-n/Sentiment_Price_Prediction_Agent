# Sentiment Price Prediction Agent

The Sentiment Price Prediction Agent combines social sentiment, news sentiment, and historical market prices to forecast the next configured price bar.

## Features

- Collects social posts through configurable Apify actors.
- Collects financial news through Exa.
- Retrieves historical prices through Yahoo Finance.
- Builds technical and sentiment-based features.
- Uses chronological out-of-sample validation.
- Generates HTML, CSV, and JSON reports.
- Retains collected sentiment and forecast history.

## Project Structure

```text
src/sentipipe/
  cli.py       Command-line entry point
  config.py    Configuration loading and validation
  features.py  Feature engineering
  history.py   Historical data and forecast tracking
  modeling.py  Prediction and validation
  pipeline.py  End-to-end asset analysis workflow
  providers.py Social, news, and price providers
  report.py    Report generation

tests/         Python test suite
config.yaml    Asset and data-source configuration
```

## Requirements

- Python 3.10 or later
- An Apify API token
- An Exa API key
- Internet access for Apify, Exa, and Yahoo Finance

## Setup

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
```

Create the local environment file:

```powershell
Copy-Item .env.template .env
```

Add the required credentials to `.env`, then configure the Apify actor IDs and input mappings in `config.yaml`.

## Run

```powershell
sentipipe --config config.yaml
```

Generated output is written to:

- `output/report.html`
- `output/predictions.csv`
- `output/predictions.json`
- `output/history/`
- `output/forecast_history.csv`

## Test

```powershell
python -m pytest
```

## Interpretation

Forecasts and validation metrics are analytical estimates, not guaranteed returns or financial advice. Support and resistance levels are descriptive. Sentiment coverage is only used when enough historical observations are available.
