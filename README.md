# Spritpreisprognose — Dieselpreisprognose mit ML

> DSI Capstone 2026 · Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo  
> Station: ARAL Dürener Str. 407, Köln · Datenquelle: Tankerkönig / MTS-K

[![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-blue)](https://github.com/felixschrader/spritpreisprognose)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit_Cloud-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/Data-CC_BY_4.0-green)](https://creativecommons.org/licenses/by/4.0/)

---

## Projektziel

Dieses Projekt analysiert und prognostiziert Dieselpreise an einer ARAL-Tankstelle in Köln. Im Mittelpunkt steht nicht nur die Prognose, sondern die **empirische Analyse des algorithmischen Preissetzungsverhaltens** der Mineralölkonzerne — insbesondere das *Rockets & Feathers*-Phänomen.

---

## Kernbefunde

### 1. Rockets & Feathers — empirisch nachgewiesen

| Brent-Bewegung | Erhöhungen | Senkungen | Asymmetrie |
|----------------|-----------|-----------|------------|
| Brent steigt   | **37.5%** | 30.4%     | +7.1 Punkte Erhöhungs-Bias |
| Brent fällt    | 28.2%     | **38.8%** | +10.6 Punkte Senkungs-Bias |
| Brent neutral  | 21.6%     | 20.7%     | symmetrisch |

> *Konsistent mit der Rockets-&-Feathers-Hypothese (Bacon 1991, Frondel et al. 2021): Tankstellen erhöhen Preise schneller als sie senken.*

### 2. Pass-Through-Rate

1 € Brent-Anstieg → **0.18–0.40 Cent** Kernpreis-Änderung (Lag 1–3 Tage).  
R² des direkten Brent-Kernpreis-Zusammenhangs: **0.89** (Niveau), **0.09** (tägliches Delta).

### 3. Residuum-Persistenz

ARAL Dürener Str. hält ihre Preisposition relativ zum NRW-Markt stabil.  
AR(1)-Autokorrelation des Residuums: **0.61** — stärkster Einzelprädiktor im Modell.

---

## ML-Modell

### Zielvariable

```
ziel = rolling_mean(kernpreis_p10, 3).shift(-2) - rolling_mean(kernpreis_p10, 3)
```

Der **Kernpreis** ist definiert als p10 der Stundenbins (Median) zwischen 13–20 Uhr — der stabile Nachmittagspreis nach dem Senkungsprozess, bereinigt von den algorithmischen Morgenspikes.

### Modell-Performance

| Metrik | Wert |
|--------|------|
| Modell | Random Forest Regressor |
| Richtungs-Accuracy Test | **67.9%** |
| Richtungs-Accuracy Val | **75.0%** |
| Baseline (Zufallsraten) | 38.6% |
| Delta über Baseline | **+29.3 Prozentpunkte** |
| MAE Test | 0.89 Cent |
| R² Test | 0.30 |
| Horizont | 2 Tage (roll=3, shift=2) |

### Feature Importance (SHAP)

| Rang | Feature | Beschreibung |
|------|---------|--------------|
| 1 | `brent_delta2` | Brent-€-Änderung vor 2 Tagen |
| 2 | `delta_kern_lag1` | Kernpreis-Delta gestern |
| 3 | `residuum_lag1` | ARAL vs. NRW-Markt gestern |
| 4 | `delta_markt_lag1` | Marktbewegung gestern |
| 5 | `tage_seit_erhoehung` | Tage seit letzter Preiserhöhung |

### Modellvergleich

| Modell | Richtung Test | R² Test | MAE Test |
|--------|--------------|---------|----------|
| Random Forest (final) | **67.9%** | **0.30** | 0.89c |
| XGBoost | 65.7% | 0.18 | 0.96c |
| Ridge Regression | 62.0% | -1.66 | 0.85c |
| LSTM | 60.4% | -0.25 | 0.62c |
| CNN | 58.2% | -0.21 | 1.05c |
| Transformer | 57.3% | -5.90 | 3.11c |
| Persistenz-Baseline | 73.6% | 0.99 | 0.33c |
| Richtungs-Baseline | 38.6% | — | 0.88c |

> *Anmerkung: Persistenz (morgen = heute) hat hohe Accuracy für absolute Preise (R²=0.99), ist aber trivial — sie sagt nie eine Richtungsänderung vorher. Unser Modell predictet die Richtungsänderung des 3-Tage-Rolling-Kernpreises.*

---

## Datenquellen & Pipeline

| Quelle | Daten | Zeitraum | Update |
|--------|-------|----------|--------|
| Tankerkönig | Preisänderungen (sekündlich) | 2019–2026 | täglich |
| FRED API | Brent Crude Futures (USD) | 2014–2026 | täglich |
| EZB API | EUR/USD-Wechselkurs | 2014–2026 | täglich |
| Barchart | Brent Intraday 1h | 2017–2026 | einmalig |
| feiertage-api.de | NRW-Feiertage | 2014–2026 | jährlich |
| OpenHolidays API | NRW-Schulferien | 2014–2026 | jährlich |
| BEHG / DEHSt | CO₂-Abgabe | 2021–2026 | jährlich |

### GitHub Actions Workflows

```
.github/workflows/
├── update_tankstellen.yml      # täglich 05:00 — Preisdaten
├── live_inference.yml          # stündlich — Stunden-Prognose (v1)
├── live_inference_tagesbasis.yml # täglich 09:00 — Tages-Prognose (v2)
├── brent_update.yml            # täglich — Brent/EUR-USD
├── feiertage_update.yml        # jährlich
└── schulferien_update.yml      # halbjährlich
```

---

## Projektstruktur

```
spritpreisprognose/
├── notebooks/
│   ├── Machine_Learning_MVP_v2.ipynb      # stündliches Klassifikationsmodell
│   └── Machine_Learning_Tagesbasis.ipynb  # tagesbasiertes Regressionsmodell
├── data/
│   ├── tankstellen_preise.parquet         # Preishistorie ARAL + Nachbarn
│   ├── tankstellen_stationen.parquet      # Stationsdaten
│   ├── brent_futures_daily.csv
│   ├── brent_futures_1h.csv               # Intraday Brent (Barchart)
│   ├── eur_usd_rate.csv
│   ├── feiertage.csv
│   ├── schulferien.csv
│   ├── externe_effekte.csv
│   ├── energiesteuer.csv
│   └── ml/
│       ├── modell_rf_markt_aral_duerener.pkl
│       ├── modell_metadaten_markt_aral_duerener.json
│       ├── prognose_tagesbasis.json        # täglich aktualisiert
│       └── aral_nrw_tagesbasis.parquet     # 585 Stationen NRW
├── dashboard.py                            # Streamlit — stündlich
├── dashboard_tagesbasis.py                 # Streamlit — täglich
├── live_inference.py                       # stündliche Inference
├── live_inference_tagesbasis.py            # tägliche Inference
└── tankerkoenig_pipeline.py               # ETL-Pipeline
```

---

## Methodology

### Kernpreis-Definition

Rohe Tankerkönig-Daten enthalten sekündliche Preisänderungen inkl. algorithmischer Morgenspikes (+15–30 Cent um 06:00 Uhr). Wir definieren den **Tageskernpreis** als:

1. Rohdaten → Stundenbins (Median pro Stunde)
2. Filter: nur Stunden 13–20 Uhr (stabil, nach Senkungsprozess)
3. p10 dieser Stunden → Kernpreis

**Begründung:** Der Scatter-Plot Tagesstunde vs. Abstand vom Median zeigt einen klaren Peak bei 06:00 Uhr (10.32 Cent mittlerer Abstand) und stabile Werte 13–20 Uhr (1.86–2.33 Cent).

### Zielvariablen-Wahl

Wir haben systematisch getestet:
- `delta_t1` (morgen vs. heute): R²=0.09, zu verrauscht
- Absolute Preise: Persistenz nicht schlagbar (R²=0.99)
- Neuronale Netze: alle 24 Modelle schlechter als Persistenz
- **`roll3_shift2`** (3-Tage-Rolling, 2 Tage voraus): R²=0.30, Richtung 67.9% ✅

### NRW-Marktanalyse

Wir haben alle 585 ARAL-Stationen in NRW analysiert (1.67M Zeilen, 2019–2026) um:
- den NRW-Marktmedian als strukturelles Signal zu extrahieren
- das stationsindividuelle Residuum (ARAL Dürener vs. Markt) zu quantifizieren
- Rockets & Feathers über einen robusten Datensatz nachzuweisen

---

## Installation & Ausführung

```bash
# Repository klonen
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env anlegen
echo "TANKERKOENIG_KEY=dein_key" > .env
echo "ANTHROPIC_API_KEY=dein_key" >> .env

# Dashboard starten
streamlit run dashboard_tagesbasis.py

# Tages-Inference ausführen
python live_inference_tagesbasis.py
```

---

## Literatur

- Bacon, R.W. (1991): *Rockets and Feathers: The Asymmetric Speed of Adjustment of UK Retail Gasoline Prices to Cost Changes*. Energy Economics, 13(3), 211–218.
- Frondel, M., Horvath, M., Sommer, S. (2021): *Rockets and Feathers in German Gasoline Markets*. Ruhr Economic Papers.
- Tankerkönig (2026): *Kraftstoffpreise Deutschland*. [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

---

## Team

| Name | Rolle |
|------|-------|
| Felix Schrader | Infrastructure, Data Mining, ML, Automation |
| Girandoux Fandio Nganwajop | ETL, EDA, Datenbankentwicklung |
| Ghislain Wamo | Datenbankarchitektur, Dashboard |

---

*DSI Continuing Education Program 2026 · Köln*
