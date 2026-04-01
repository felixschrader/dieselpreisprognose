# Diesel price forecast · DSI Capstone 2026

[🇩🇪](README.md)

MVP for **short-term diesel price forecasting** at a reference filling station. **Model:** Random Forest trained on **per-calendar-day features** (derived from price series, market context, and external drivers). Capstone in the data science programme at [**DSI Berlin**](https://data-science-institute.de/); prototype build window approx. **two weeks**.

[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dieselpreisprognose.streamlit.app)

| | |
|--|--|
| **Live dashboard** | [dieselpreisprognose.streamlit.app](https://dieselpreisprognose.streamlit.app) |
| **ML workbook** | [Machine_Learning_Tagesbasis.ipynb](https://github.com/felixschrader/dieselpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb) |

**Reference site:** ARAL · Dürener Str. 407 · 50858 Cologne — [station page](https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400) · Raw prices: [Tankerkönig](https://www.tankerkoenig.de) / MTS-K

**Team:** [Felix Schrader](https://www.linkedin.com/in/felixschrader/) · [Girandoux Fandio Nganwajop](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) · [Ghislain Djifag Wamo](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Djifag%20Wamo)

---

## Overview

- **Problem:** Prices **move a lot within a single day** (many updates, short spikes); local competition adds noise. For a stable signal we **summarise the day** — the forecast targets this **day-level core logic**, not the exact pump price at a given minute.
- **Deliverables:** Streamlit dashboard (KPIs, charts, context), daily inference via GitHub Actions, trained artefacts under `data/ml/`.
- **Scope:** One station, **diesel**; architecture intended to scale later (more sites, grades). We **do not** claim a full **causal proof** of classic oil-to-pump “rockets and feathers” patterns — analysis stays **descriptive / model-based**.
- **Audience:** People making refuelling decisions, stakeholders, technical reviewers.

---

## Methodology

### Core price (target proxy)

| Step | Content |
|------|---------|
| Hourly value | All reports in an hour collapse to **one** price (**median** = middle value, robust to outliers). |
| Day window | **13:00–20:00 only** — empirically calmer than, e.g., early morning. |
| One price per day | From hourly prices in that window we derive **one** daily core price — see **P10** below. |

**What is P10 (10th percentile)?** Imagine all hourly prices for a day in the 13:00–20:00 window **sorted from low to high**. The **10th percentile** is the value **below** which about **10%** of those prices fall and **90%** lie above. In plain terms: a **rather low** reference for the day — not the most expensive moment and not driven by a single upward spike. That makes the daily core price **more conservative** and **more comparable** across days; brief peaks do not dominate it.

*(In statistics software this is often “quantile 0.10”; in the project we call it **P10**.)*

### Market & features

- **Oil & FX → pump:** How movements in **Brent** and **EUR/USD** show up in observed prices (captured as model inputs).
- **Distance from market middle:** How far the reference ARAL sits from the **median of many ARAL stations in North Rhine-Westphalia** — roughly “more expensive / cheaper than the NRW ARAL middle”. *(In the notebook: **residual**.)*
- **Regime:** e.g. how many days since the last noticeable **price up or down**.
- NRW context: **585** ARAL sites in NRW (per metadata) provide the market frame for the focal station.

### Target variable

- **Idea:** Not the raw day-to-day jump, but the **direction** in which the core price moves when **lightly smoothed over several days**.
- **Implementation (technical):** Build a **rolling 3-day mean** of daily core prices (each point = average over three consecutive days — **less day-to-day noise**). The target is the **difference** between that mean **today** and the mean **two steps ahead** along the daily series. In code this appears as `roll3` and `shift(-2)` — meaning **calendar days** in a gap-free daily index, not stock-market “trading days”.
- **Inference anchor:** The **core price of the last fully evaluated day** (often **yesterday** in practice). Statements are on this **core-price level**, not the “price right now” at the nozzle.

### Model & features (MVP)

- **Model:** **Random Forest** — many **decision trees** combined (ensemble); hyperparameters chosen with **tuning** and **time-aware cross-validation** (time order preserved, no random shuffling). The notebook also explores Ridge, XGBoost, neural baselines.
- **SHAP:** A method that makes **which inputs influence the model how much** inspectable — not a pure black box.
- **Model inputs (excerpt; internal column names):** e.g. oil-price change, lagged core and market price changes, distance to market middle, weekday, market volatility — full list and derivation in the [notebook](https://github.com/felixschrader/dieselpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb) (`brent_delta2`, `delta_kern_lag1/2`, …).

### Train / test & persistence

- **Train and test sets** are split **in time** (older data trains, newer data tests — **no** random shuffle so **future** information cannot leak into training). Artefacts: `data/ml/` (model, metadata, forecast JSON).

---

## Evaluation

- Metrics from **model metadata** (e.g. **directional accuracy** on the test set, **MAE** = mean absolute error on the target, **R²** = share of variance explained — for orientation only, **not** a guarantee for minute-level prices).
- **Direction baseline:** Compare whether **signs** of target *y* and prediction *ŷ* match (up vs. down under the project definition). The **naive** “always predict zero” baseline has accuracy equal to the **fraction of test days with *y* ≤ 0** — **not** automatically 50%. Many positive *y* → low baseline; balanced targets → baseline near 50%.
- **Other metrics** (notebook): e.g. **corridor** (direction correct **and** error below a small threshold), evaluations only for **large** |*y*| — each answers a **different** question than raw sign accuracy.
- **Dashboard (retrospective):** “Direction correct” uses a **±0.5 ct** bucketing — easier to read, **not the same** number as the strict sign metric in the notebook.

---

## System

**Automation:** [GitHub Actions](https://github.com/felixschrader/dieselpreisprognose/tree/main/.github/workflows) — station/price history, Brent & EUR/USD, weather, public/school holidays, CO₂ levy, hourly and daily inference (cron schedules in the YAML files).

**Dashboard:** `scripts/dashboard.py` — Plotly, map (OpenStreetMap / Leaflet), optional copy via **Anthropic API**.

### Repository layout

```text
dieselpreisprognose/
├── data/ml/                 # model, metadata, forecast JSON
├── scripts/
│   ├── dashboard.py
│   ├── inference/
│   ├── features/
│   └── pipeline/
├── notebooks/
│   └── Machine_Learning_Tagesbasis.ipynb
├── papers/
├── LICENSE
├── README.md                # German (default on GitHub)
├── README.en.md             # this file
└── requirements.txt
```

### Tech stack (excerpt)

| Area | Technology |
|------|------------|
| Core | Python, pandas, numpy, scikit-learn, joblib, Streamlit, Plotly |
| Markets | yfinance (Brent), ECB API (EUR/USD) |
| Prices | Tankerkönig JSON API |
| Calendar / weather | feiertage-api.de, OpenHolidays, DWD OpenData |
| Other | DEHSt (CO₂), Anthropic (dashboard text), OSM / Leaflet |

---

## References & data licence

Supporting PDFs in [`papers/`](papers/).

| Type | Title / source | Author / editor | Year | Notes |
|------|----------------|-----------------|------|-------|
| Literature | *Rockets and Feathers: The Asymmetric Speed of Adjustment…* | Bacon, R.W. | 1991 | Energy Economics |
| Literature | *Rockets and Feathers in German Gasoline Markets* | Frondel, Horvath, Sommer | 2021 | Ruhr Economic Papers |
| Data | Tankerkönig / MTS-K | — | — | [tankerkoenig.de](https://www.tankerkoenig.de) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| PDF | *Benzinpreise vorhersagen …* | Golem.de | 2026 | ML & fuel prices |
| PDF | *Branchenuntersuchung Kraftstoffmarkt* | Schwarz, M. | 2022 | Industry report |
| PDF | *Die Preisbindung im Oligopol* / Freilaw | Legner, S. | 2014 | Fuel sector |
| PDF | *Mittels Deep Learning Benzinpreise vorhersagen* | Devoteam | n/a | Expert view |
| PDF | *Price Matching and Edgeworth Cycles* | Wilhelm, S. | 2019 | SSRN 2708630 |
| PDF | *Wie sich die Benzinpreise in Deutschland entwickeln* | Devoteam | n/a | Expert view |

---

## Local development

```bash
git clone git@github.com:felixschrader/dieselpreisprognose.git
cd dieselpreisprognose
pip install -r requirements.txt

echo "TANKERKOENIG_KEY=…" > .env
echo "ANTHROPIC_API_KEY=…" >> .env   # optional, for dashboard text features

streamlit run scripts/dashboard.py
python scripts/inference/live_inference_tagesbasis.py
```

Development was mostly on **`main`** without a full PR history; substantive choices are documented in the README, notebook, and model metadata.

---

## Licence

- **Source code:** [MIT](LICENSE)
- **Raw station data (Tankerkönig):** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## AI-assisted development

**Cursor** and **Claude Code** were used primarily for dashboard implementation, Plotly styling, CI/CD configuration, and editorial drafting. **Domain analysis, feature design, target-definition, model comparison, evaluation methodology, and accountability** remain with the team.

---

## Team

| Name | Role |
|------|------|
| [Felix Schrader](https://www.linkedin.com/in/felixschrader/) | Infrastructure, data engineering, ML, automation |
| [Girandoux Fandio Nganwajop](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) | ETL, EDA, data engineering |
| [Ghislain Djifag Wamo](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Djifag%20Wamo) | Data architecture, dashboard |

*Data Science Institute · Professional programme 2026 · Berlin*
