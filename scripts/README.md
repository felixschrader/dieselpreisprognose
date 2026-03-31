# Scripts Overview

This folder contains all executable Python scripts, grouped by purpose.

## `dashboard`

- `dashboard.py`: Streamlit dashboard app for live KPIs, forecasts, and model-performance views.

## `inference`

- `inference/live_inference.py`: Runs hourly inference and updates `data/ml/prognose_aktuell.json`.
- `inference/live_inference_tagesbasis.py`: Runs daily inference and updates `data/ml/prognose_tagesbasis.json`.

## `features`

- `features/brent_price.py`: Updates Brent crude oil feature time series.
- `features/eur_usd_rate.py`: Updates EUR/USD exchange-rate feature time series.
- `features/wetter_koeln.py`: Updates weather feature data for Cologne/Bonn station.
- `features/feiertage.py`: Updates German public holiday features.
- `features/schulferien.py`: Updates German school holiday features.
- `features/co2_abgabe.py`: Updates CO2 levy feature series.
- `features/energiesteuer.py`: Generates/updates energy-tax feature series.
- `features/externe_effekte.py`: Builds consolidated external-effects feature data.

## `pipeline`

- `pipeline/tankerkoenig_pipeline.py`: Main ETL pipeline for Tankerkönig raw data to curated parquet outputs.
- `pipeline/backfill_prognose_log.py`: Backfills historical forecast-log records.

## Quick run examples

```bash
# Dashboard
streamlit run scripts/dashboard.py

# Hourly inference
python scripts/inference/live_inference.py

# Daily inference
python scripts/inference/live_inference_tagesbasis.py
```
