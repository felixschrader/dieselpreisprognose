# DSI Capstone Project 2026 — MVP Kraftstoffpreisprognose (Diesel)

## Live-Dashboard & Profile

**Streamlit-App (Produktion):**  
[**https://spritpreisprognose.streamlit.app**](https://spritpreisprognose.streamlit.app)

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://spritpreisprognose.streamlit.app)

**LinkedIn (Team):**

[![LinkedIn Felix](https://img.shields.io/badge/LinkedIn-Felix_Schrader-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/felixschrader/)
[![LinkedIn Girandoux](https://img.shields.io/badge/LinkedIn-Girandoux_Fandio-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/girandoux-fandio-08628bb9/)
[![LinkedIn Ghislain](https://img.shields.io/badge/LinkedIn-Ghislain_Wamo-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo)

> Capstone-Projekt im 6-monatigen Data-Science-Weiterbildungsprogramm am **Data Science Institute** ([DSI](https://data-science-institute.de/)).  
> **Team:** Felix Schrader, Girandoux Fandio Nganwajop, Ghislain Wamo  
> **Station:** ARAL Dürener Str. 407, Köln · Datenquelle: Tankerkönig / MTS-K

[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=flat&logo=github)](https://github.com/felixschrader/spritpreisprognose)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?style=flat&logo=githubactions&logoColor=white)](https://github.com/felixschrader/spritpreisprognose/actions)
[![License Daten](https://img.shields.io/badge/Daten-CC_BY_4.0-green?style=flat)](https://creativecommons.org/licenses/by/4.0/)

---

## 1) Kontext

Dieses Projekt entstand als praxisnahes Capstone unter klaren Rahmenbedingungen: Das Gesamtprogramm läuft sechs Monate, das **konkrete MVP-Umsetzungsfenster** für diesen Prototyp lag bei etwa **zwei Wochen**.

Ziel war eine **robuste und operationalisierbare Kurzfristprognose** für zunächst **eine lokale Station**, mit einer Architektur, die später erweitert werden kann auf:
- weitere Stationen,
- lokale Wettbewerbsdynamik,
- weitere Kraftstoffarten (E5/E10).

**Aktueller Produktionsfokus:** Diesel an der ARAL Dürener Str. 407, Köln.

---

## 2) Zielgruppe

Primäre Nutzergruppen des MVP sind:
- Fahrer:innen mit kurzfristigen Tankentscheidungen,
- Projektstakeholder zur Bewertung des praktischen Nutzens,
- technische Reviewer mit Interesse an End-to-End-ML unter Zeitdruck.

---

## 3) Kernfrage

Wie lässt sich eine **robuste, nachvollziehbare Kurzfristprognose** aufbauen, obwohl:
- starke Intraday-Preiszylken auftreten,
- lokale Wettbewerbsreaktionen die Dynamik prägen,
- hochfrequente Rohdaten stark verrauscht sind?

---

## 4) Methodik (Argumentationskette)

### 4.1 Warum ein Kernpreis-Proxy?

Rohpreise sind intraday sehr volatil. Für ein stabiles Zielsignal definieren wir einen **Kernpreis**, der über Tage besser vergleichbar und weniger verrauscht ist.

### 4.2 Kernpreis-Definition

1. Aggregation der Rohpreis-Events in Stunden-Bins (Median pro Stunde).
2. Fokus auf das empirisch stabilste Zeitfenster: **13:00–20:00**.
3. Verwendung von **P10** in diesem Fenster als täglicher Kernpreis-Proxy.

**Begründung:** Unterdrückt Morgenspike-Artefakte, bleibt konservativ für Tankzeitpunkte und verbessert die zeitliche Vergleichbarkeit für das Modell.

### 4.3 Marktstruktur-Signale

Neben stationsspezifischer Dynamik fließen ein:
- **Pass-through-Verhalten** (Öl-/Währungsimpulse auf den lokalen Kernpreis),
- **Residuum-Persistenz** (stationsrelativer Anteil gegenüber dem Markt).

Im MVP wird **kein finaler kausal Nachweis** von Rockets-and-Feathers beansprucht; die Analyse bleibt als **Evidenzmuster** formuliert und kann in Folgeprojekten vertieft werden.

---

## 5) Architektur und Modellproduktion

### 5.1 ETL und EDA

- ETL ingestiert Tankerkönig-Daten, aktualisiert kuratierte Parquet/CSV-Artefakte und sichert historische Kontinuität.
- EDA dient der Identifikation stabiler Zeitfenster, Zyklusmuster und robuster Zielkandidaten.

### 5.2 ML-Pipeline

- Feature-Sets kombinieren gelaggte Kernpreis-Deltas, Marktkontext und externe Treiber.
- Ein stufenweiser Experimentprozess vergleicht alternative Horizonte, Shifts und Zieldefinitionen.

### 5.3 Zielvariable (iterative Suche)

Finale Wahl (Beispiel):

`roll3_shift2`:  
`rolling_mean(core_price, 3).shift(-2) - rolling_mean(core_price, 3)`

### 5.4 Feature Engineering

- gelaggte stationsbezogene Kernpreis-Signale,
- marktrelative Residuen,
- externe Variablen (Brent, EUR/USD, Kalender, Wetter, CO2-/Steuerkontext),
- einfache Regime-Indikatoren (z. B. Tage seit letzter Erhöhung).

### 5.5 Train/Test-Split

Zeitlicher Split (kein zufälliges Shuffle), um kausale Reihenfolge zu wahren und Leakage zu vermeiden.

### 5.6 Modellauswahl

**Random Forest Regressor** auf der gewählten Zielvariable — im MVP ein robuster Kompromiss gegenüber alternativen Modellfamilien.

### 5.7 Evaluation (MVP-Stand)

Referenzmetriken (aktuell):
- Richtungsgenauigkeit (Test): ~67,9 %
- MAE (Test): ~0,89 Cent
- R² (Test): ~0,30

### 5.8 Modell-Persistenz

Trainierte Artefakte liegen unter `data/ml/` und werden von Inference-Skripten und dem Dashboard genutzt.

---

## 6) Automatisierung mit GitHub Actions

Wiederkehrende Daten- und Modellupdates laufen über GitHub Actions. **Cron-Zeiten in UTC.**

| Workflow | Zweck | Zeitplan (UTC) |
|---|---|---|
| `update_tankstellen.yml` | Stationspreishistorie | täglich `04:00` |
| `live_inference.yml` | Stündliche Kurzfrist-Inference | stündlich `:15` |
| `live_inference_tagesbasis.yml` | Tägliche Tagesbasis-Inference | täglich `09:00` |
| `update_brent_prices.yml` | Brent | alle 2 h `:00` |
| `update_eur_usd.yml` | EUR/USD | alle 2 h `:10` |
| `update_wetter.yml` | Wetter | täglich `04:30` |
| `update_co2_abgabe.yml` | CO₂-Abgabe | dienstags `06:00` |
| `update_feiertage.yml` | Feiertage | jährlich 1. Jan `06:00` |
| `update_schulferien.yml` | Schulferien | jährlich 2. Jan `07:00` |
| `backfill.yml` | Historisches Backfill | nur manuell |

---

## 7) Streamlit-Dashboard

Implementiert in `scripts/dashboard.py` u. a. mit:
- Modellausgaben und KPI-Panels,
- Kurzfristprognose-Visualisierung,
- erklärenden Texten (Anthropic API),
- Kartenkontext (OpenStreetMap),
- angepasstem Theme für Lesbarkeit.

---

## 8) Projektstruktur (Auszug)

```text
spritpreisprognose/
├── data/
│   ├── tankstellen_preise.parquet
│   ├── tankstellen_stationen.parquet
│   ├── brent_futures_daily.csv
│   ├── eur_usd_rate.csv
│   ├── feiertage.csv
│   ├── schulferien.csv
│   ├── wetter_koeln.csv
│   └── ml/
│       ├── prognose_aktuell.json
│       ├── prognose_tagesbasis.json
│       ├── modell_rf_markt_aral_duerener.pkl
│       └── modell_metadaten_markt_aral_duerener.json
├── scripts/
│   ├── dashboard.py
│   ├── README.md
│   ├── inference/
│   ├── features/
│   └── pipeline/
├── notebooks/
├── papers/
└── requirements.txt
```

---

## 9) Tech-Stack (Kern)

- Python · pandas / numpy · **scikit-learn** · Streamlit · Plotly · GitHub Actions  
- APIs: Tankerkönig / MTS-K, Anthropic (Textgenerierung), OpenStreetMap

---

## 10) Literatur

Die Literaturbasis des Projekts besteht aus **zitierten wissenschaftlichen Quellen**, der **Datenlizenz** sowie aus **PDFs im Ordner `papers/`** (Begleitliteratur, Reports, Artikel — versioniert im Repository).

### Wissenschaftliche Grundlagen (Zitation im Projekt)

- Bacon, R.W. (1991): *Rockets and Feathers: The Asymmetric Speed of Adjustment of UK Retail Gasoline Prices to Cost Changes*. Energy Economics, 13(3), 211–218.
- Frondel, M., Horvath, M., Sommer, S. (2021): *Rockets and Feathers in German Gasoline Markets*. Ruhr Economic Papers.

### Datenrecht (Tankerkönig)

- Tankerkönig / MTS-K: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

### Papers im Repository (`papers/`)

| Datei | Titel / Autor(en) | Jahr | Kurzbeschreibung |
|---|---|---:|---|
| `Benzinpreise vorhersagen_ Effizientes, maschinelles Lernen für Sparfüchse - Golem.de.pdf` | *Benzinpreise vorhersagen: Effizientes, maschinelles Lernen für Sparfüchse* (Golem.de) | 2026¹ | Online-Artikel zu ML-gestützter Preisprognose |
| `Bericht_BU_Kraftstoffe_2022_final.pdf` | *Branchenuntersuchung Kraftstoffmarkt* (Schwarz, Moritz) | 2022 | Branchenbericht (Word/PDF-Metadaten) |
| `freilaw2014.pdf` | *Die Preisbindung im Oligopol* / *Preisbildung im Oligopol* (Legner, Sarah; Freilaw 1/2014) | 2014 | Juristische Fachzeitschrift, Bezug Sektoruntersuchung Kraftstoffe |
| `Mittels Deep Learning Benzinpreise vorhersagen _ Devoteam.pdf` | *Mittels Deep Learning Benzinpreise vorhersagen* (Devoteam Expert View) | k. A. | Firmen-Blogbeitrag (Deep Learning, Benzinpreise) |
| `ssrn-2708630.pdf` | *Price Matching and Edgeworth Cycles* (Wilhelm, Sascha; Goethe-Uni Frankfurt) | 2019 | Working Paper, empirisch u. a. deutscher Tankstellenmarkt (Tankerkönig-Daten) |
| `Wie sich die Benzinpreise in Deutschland entwickeln _ Devoteam.pdf` | *Wie sich die Benzinpreise in Deutschland entwickeln* (Devoteam Expert View) | k. A. | Firmen-Blogbeitrag zur Preisentwicklung DE |

¹ Datum laut PDF-Erstellung/Screenshot im Dokument (Januar 2026); Primärquelle ist der Golem-Artikel online.

---

## 11) Lokaler Start

```bash
git clone git@github.com:felixschrader/spritpreisprognose.git
cd spritpreisprognose
pip install -r requirements.txt

# optional: lokale Secrets
echo "TANKERKOENIG_KEY=dein_key" > .env
echo "ANTHROPIC_API_KEY=dein_key" >> .env

streamlit run scripts/dashboard.py
python scripts/inference/live_inference_tagesbasis.py
```

---

## Team

| Name | Rolle | LinkedIn |
|---|---|---|
| Felix Schrader | Infrastruktur, Data Engineering, ML, Automatisierung | [Profil](https://www.linkedin.com/in/felixschrader/) |
| Girandoux Fandio Nganwajop | ETL, EDA, Data Engineering | [Profil](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) |
| Ghislain Wamo | Datenarchitektur, Dashboard | [Suche](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo) |

---

## KI-Prompt für die Abschlusspräsentation

Fertiger Kontext-Prompt (Argumentationskette, Zielgruppe, Kontext, Links) zum Kopieren in ein KI-Tool:  
**[PRESENTATION_KI_PROMPT.md](PRESENTATION_KI_PROMPT.md)**

---

*DSI Weiterbildung 2026 · Köln*
