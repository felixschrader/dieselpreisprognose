# Dieselpreisprognose · DSI Capstone 2026

MVP zur **Kurzfristprognose von Dieselpreisen** an einer Referenz-Tankstelle (Random Forest auf Tagesfeatures). Capstone im Data-Science-Programm am [**DSI Berlin**](https://data-science-institute.de/); Umsetzungsfenster des Prototyps ca. **zwei Wochen**.

[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dieselpreisprognose.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=flat&logo=github)](https://github.com/felixschrader/dieselpreisprognose)
[![Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/felixschrader/dieselpreisprognose/actions)

| | |
|--|--|
| **Live-Dashboard** | [dieselpreisprognose.streamlit.app](https://dieselpreisprognose.streamlit.app) |
| **Repository** | [github.com/felixschrader/dieselpreisprognose](https://github.com/felixschrader/dieselpreisprognose) |
| **ML-Arbeitsgrundlage** | [Machine_Learning_Tagesbasis.ipynb](https://github.com/felixschrader/dieselpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb) |

**Referenz:** ARAL · Dürener Str. 407 · 50858 Köln — [Stationsseite](https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400) · Rohpreise: [Tankerkönig](https://www.tankerkoenig.de) / MTS-K

**Team:** Felix Schrader · Girandoux Fandio Nganwajop · Ghislain Wamo

---

## Überblick

- **Problem:** Intraday-Volatilität und lokale Wettbewerbsdynamik überlagern ein nutzbares Tages-Signal; Ziel ist eine **nachvollziehbare** Kurzfristprognose auf **Tages-/Kernpreis-Ebene**, nicht Minuten-Spot.
- **Lieferobjekt:** Streamlit-Dashboard (KPIs, Visualisierung, Kontext), tägliche Inferenz per GitHub Actions, trainierte Artefakte unter `data/ml/`.
- **Scope:** Eine Station, **Diesel**; Architektur soll später erweiterbar sein (weitere Standorte, Sorten). **Kein** beanspruchter finaler **kausaler** Rockets-and-Feathers-Nachweis — Evidenz auf Modell-/Datenebene.
- **Zielgruppen:** Endnutzer:innen mit Tankentscheidung, Stakeholder, technische Reviewer:innen.

---

## Methodik

### Kernpreis (Ziel-Proxy)

| Schritt | Inhalt |
|--------|--------|
| Aggregation | Stunden-Bins, **Median** pro Stunde |
| Fenster | **13–20 Uhr** (empirisch stabiler als Morgenstunden) |
| Tageswert | **P10** der Stundenpreise im Fenster → konservativer Tagesanker, robust gegen Spitzen |

### Markt & Features

- **Pass-through** (Brent/Währung), **Residuum** Station vs. NRW-Markt-Referenz, Regime-Indikatoren (z. B. Tage seit letzter Anpassung).
- NRW-Markt im Setup: **ARAL-Stationen in NRW** (Metadaten: **585** Standorte) als Kontext für die eigene Station.

### Zielvariable

- **Idee:** Richtungsänderungen des **geglätteten** Kernpreises über mehrere Tage, nicht rohes Tagesdelta.
- **Umsetzung:** Differenz aus **gleitendem 3-Tage-Mittel** (`roll3`) und demselben Mittel **zwei Index-Schritte voraus** (`shift(-2)` auf der **täglichen** Reihe — i. d. R. zwei Kalendertage bei lückenloser Tagesreihe, keine Börsen-Handelskalender-Logik).
- **Inferenz-Bezug:** **Kernpreis des letzten geschlossenen Tages** (praktisch oft **gestern**); Aussage auf **Kernpreis-Ebene**, nicht „Preis genau jetzt an der Säule“.

### Modell & Features (MVP)

- **Modell:** Random Forest Regressor (Hyperparameter-Tuning, zeitliche CV). Im Notebook zusätzlich Ridge, XGBoost, neuronale Baselines — **SHAP** zur Einordnung.
- **Feature-Liste (Auszug):** `brent_delta2`, `delta_kern_lag1/2`, `delta_markt_lag1/2`, `residuum_lag1`, `tage_seit_erhoehung`, `tage_seit_senkung`, `wochentag`, `ist_montag`, `markt_std` — Details im [Notebook](https://github.com/felixschrader/dieselpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb).

### Train/Test & Persistenz

- Zeitlicher Split (kein Shuffle). Artefakte: `data/ml/` (Modell, Metadaten, Prognose-JSON).

---

## Evaluation

- Kennzahlen (u. a. Richtungsgenauigkeit Test, MAE, R²) aus **Modell-Metadaten** — Orientierung, keine Garantie für Minutenpreise.
- **Baseline Richtung:** Vorzeichen-Vergleich mit *y* und *ŷ*; naive Vorhersage „immer 0“ entspricht einer Trefferquote = **Anteil Testtage mit *y* ≤ 0** (nicht fix 50 %). Schiefe Zielverteilung → niedrige Baseline; symmetrische → nahe 50 %.
- **Weitere Metriken** (Notebook): Korridor (Richtung + Abweichung unter Schwelle), Auswertungen bei relevantem |*y*| — jeweils andere Fragestellung als reine Vorzeichen-Accuracy.
- **Dashboard (retro):** „Richtung korrekt“ nutzt eine **±0,5-ct-Klassierung** — laienfreundlicher, **nicht identisch** mit der strengen Vorzeichen-Metrik im Notebook.

---

## System

**Automatisierung:** [GitHub Actions](https://github.com/felixschrader/dieselpreisprognose/tree/main/.github/workflows) — u. a. Tankstellen-/Preishistorie, Brent & EUR/USD, Wetter, Feiertage/Schulferien, CO₂-Abgabe, stündliche und tägliche Inferenz (Cron in den YAML-Dateien).

**Dashboard:** `scripts/dashboard.py` — Plotly, Karte (OpenStreetMap/Leaflet), optionale Texte per **Anthropic API**.

### Repository-Struktur

```text
dieselpreisprognose/
├── data/ml/                 # Modell, Metadaten, Prognose-JSON
├── scripts/
│   ├── dashboard.py
│   ├── inference/
│   ├── features/
│   └── pipeline/
├── notebooks/
│   └── Machine_Learning_Tagesbasis.ipynb
├── papers/
├── LICENSE
└── requirements.txt
```

### Tech-Stack (Auszug)

| Bereich | Technologie |
|---------|-------------|
| Core | Python, pandas, numpy, scikit-learn, joblib, Streamlit, Plotly |
| Märkte | yfinance (Brent), EZB API (EUR/USD) |
| Preise | Tankerkönig JSON-API |
| Kalender / Wetter | feiertage-api.de, OpenHolidays, DWD OpenData |
| Sonstiges | DEHSt (CO₂), Anthropic (Dashboard-Texte), OSM/Leaflet |

---

## Literatur & Datenlizenz

Begleitdokumente und PDFs im Ordner [`papers/`](papers/).

| Art | Titel / Quelle | Autor / Herausgeber | Jahr | Kurzinfo |
|-----|----------------|---------------------|------|----------|
| Fachliteratur | *Rockets and Feathers: The Asymmetric Speed of Adjustment…* | Bacon, R.W. | 1991 | Energy Economics |
| Fachliteratur | *Rockets and Feathers in German Gasoline Markets* | Frondel, Horvath, Sommer | 2021 | Ruhr Economic Papers |
| Datengrundlage | Tankerkönig / MTS-K | — | — | [tankerkoenig.de](https://www.tankerkoenig.de) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| PDF | *Benzinpreise vorhersagen …* | Golem.de | 2026 | ML & Benzinpreise |
| PDF | *Branchenuntersuchung Kraftstoffmarkt* | Schwarz, M. | 2022 | Branchenbericht |
| PDF | *Die Preisbindung im Oligopol* / Freilaw | Legner, S. | 2014 | Kraftstoffsektor |
| PDF | *Mittels Deep Learning Benzinpreise vorhersagen* | Devoteam | k. A. | Expert View |
| PDF | *Price Matching and Edgeworth Cycles* | Wilhelm, S. | 2019 | SSRN 2708630 |
| PDF | *Wie sich die Benzinpreise in Deutschland entwickeln* | Devoteam | k. A. | Expert View |

---

## Lokale Entwicklung

```bash
git clone git@github.com:felixschrader/dieselpreisprognose.git
cd dieselpreisprognose
pip install -r requirements.txt

echo "TANKERKOENIG_KEY=…" > .env
echo "ANTHROPIC_API_KEY=…" >> .env   # optional, für Dashboard-Texte

streamlit run scripts/dashboard.py
python scripts/inference/live_inference_tagesbasis.py
```

Entwicklung überwiegend auf **`main`** ohne durchgängige PR-Historie; fachliche Entscheidungen in README, Notebook und Metadaten dokumentiert.

---

## Lizenz

- **Quellcode:** [MIT](LICENSE)
- **Tankstellenrohdaten (Tankerkönig):** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## KI-gestützte Entwicklung

Zur Implementierung und Textentwürfen wurden u. a. **Cursor** und **Claude Code** genutzt. **Architektur, Modellwahl, Bewertung und inhaltliche Verantwortung** liegen beim Team.

---

## Team

| Name | Rolle | LinkedIn |
|------|-------|----------|
| Felix Schrader | Infrastruktur, Data Engineering, ML, Automatisierung | [Profil](https://www.linkedin.com/in/felixschrader/) |
| Girandoux Fandio Nganwajop | ETL, EDA, Data Engineering | [Profil](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) |
| Ghislain Wamo | Datenarchitektur, Dashboard | [Suche](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo) |

*Data Science Institute · Weiterbildung 2026 · Berlin*
