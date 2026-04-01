# Dieselpreisprognose · DSI Capstone 2026

MVP zur **Kurzfristprognose von Dieselpreisen** an einer Referenz-Tankstelle. **Modell:** Random Forest — trainiert auf **Merkmalen pro Kalendertag** (abgeleitet aus Preisverläufen, Markt und Umfeld). Capstone im Data-Science-Programm am [**DSI Berlin**](https://data-science-institute.de/); Umsetzungsfenster des Prototyps ca. **zwei Wochen**.

[![Streamlit](https://img.shields.io/badge/Streamlit-Live_Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://dieselpreisprognose.streamlit.app)

| | |
|--|--|
| **Live-Dashboard** | [dieselpreisprognose.streamlit.app](https://dieselpreisprognose.streamlit.app) |
| **ML-Arbeitsgrundlage** | [Machine_Learning_Tagesbasis.ipynb](https://github.com/felixschrader/dieselpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb) |

**Referenz:** ARAL · Dürener Str. 407 · 50858 Köln — [Stationsseite](https://tankstelle.aral.de/koeln/duerener-strasse-407/20185400) · Rohpreise: [Tankerkönig](https://www.tankerkoenig.de) / MTS-K

**Team:** [Felix Schrader](https://www.linkedin.com/in/felixschrader/) · [Girandoux Fandio Nganwajop](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) · [Ghislain Wamo](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo)

---

## Überblick

- **Problem:** Preise **schwanken stark innerhalb eines Tages** (viele Meldungen, kurzfristige Sprünge); dazu kommt lokaler Wettbewerb. Für ein belastbares Signal fassen wir den Tag **zusammen** — die Prognose bezieht sich auf diese **Tages-Kernlogik**, nicht auf den exakten Minutenpreis an der Säule.
- **Lieferobjekt:** Streamlit-Dashboard (KPIs, Visualisierung, Kontext), tägliche Inferenz per GitHub Actions, trainierte Artefakte unter `data/ml/`.
- **Scope:** Eine Station, **Diesel**; Architektur soll später erweiterbar sein (weitere Standorte, Sorten). Es wird **kein** wissenschaftlich abgeschlossener **Ursachen-Nachweis** für klassische „Rockets-and-Feathers“-Muster aus dem Ölpreis auf den Zapfsäulenpreis beansprucht — die Auswertung bleibt **deskriptiv/modellbasiert**.
- **Zielgruppen:** Endnutzer:innen mit Tankentscheidung, Stakeholder, technische Reviewer:innen.

---

## Methodik

### Kernpreis (Ziel-Proxy)

| Schritt | Inhalt |
|--------|--------|
| Stundenwert | Alle Meldungen einer Stunde werden zu **einem** Preis zusammengefasst (**Median** = mittlerer Wert, robust gegen Ausreißer). |
| Tagesfenster | Nur **13–20 Uhr** — in den Daten ruhiger als z. B. der frühe Morgen. |
| Ein Preis pro Tag | Aus den Stundenpreisen in diesem Fenster wird **ein** Tages-Kernpreis gebildet — siehe **P10** unten. |

**Was ist P10 (10. Perzentil)?** Stellen Sie sich alle Stundenpreise eines Tages im Fenster 13–20 Uhr der **Größe nach sortiert** vor. Das **10. Perzentil** ist der Wert, **unter** dem etwa **10 %** dieser Preise liegen und **90 %** darüber. Umgangssprachlich: ein **eher niedriger** Referenzpreis für den Tag — nicht der teuerste Moment und nicht ein einzelner Ausreißer nach oben. So wird der Tages-Kernpreis **konservativer** und **vergleichbarer** über Tage hinweg; einzelne kurze Spitzen dominieren ihn nicht.

*(In Statistik-Software heißt das u. a. „quantile 0.10“; im Projekt kurz **P10**.)*

### Markt & Features

- **Öl & Währung → Tankstelle:** Wie stark Bewegungen von **Brent** und **Euro/Dollar** sich in den beobachteten Preisen **widerspiegeln** (im Modell als Merkmale erfasst).
- **Abstand zur Marktmitte:** Wie weit die Referenz-ARAL vom **Median vieler ARAL-Stationen in NRW** liegt — grob: „teurer/günstiger als der NRW-ARAL-Durchschnitt“. *(Im Notebook: **Residuum**.)*
- **Regime:** z. B. wie viele Tage seit der letzten spürbaren **Preiserhöhung oder -senkung** vergangen sind.
- NRW-Kontext: **585** ARAL-Standorte in NRW (laut Metadaten) bilden den Markt-Bezug für die eigene Station.

### Zielvariable

- **Idee:** Nicht der rohe Sprung von heute auf morgen, sondern die **Richtung**, in die sich der Kernpreis **über mehrere Tage hinweg leicht geglättet** bewegt.
- **Umsetzung (technisch):** Zuerst wird aus den Tages-Kernpreisen ein **gleitendes 3-Tage-Mittel** gebildet (jeder Punkt = Durchschnitt über drei aufeinanderfolgende Tage — **weniger Tagesrauschen**). Die Zielgröße ist die **Differenz** zwischen diesem Mittel **heute** und dem Mittel **zwei Tage weiter in der Zukunft** in der täglichen Reihe. In Code heißt das u. a. `roll3` und `shift(-2)` — gemeint sind **Kalendertage** in einer lückenlosen Tagesliste, keine Börsen-„Handelstage“.
- **Inferenz-Bezug:** Ausgangspunkt ist der **Kernpreis des zuletzt vollständig ausgewerteten Tages** (in der Praxis oft **gestern**). Die Aussage gilt auf dieser **Kernpreis-Ebene**, nicht für den Minutenpreis „gerade jetzt“.

### Modell & Features (MVP)

- **Modell:** **Random Forest** — viele **Entscheidungsbäume** werden kombiniert (Ensemble); Parameter wurden mit **Hyperparameter-Tuning** und **zeitlicher Kreuzvalidierung** gewählt (Training respektiert die Zeitachse, kein zufälliges Mischen). Im Notebook zusätzlich Ridge, XGBoost, neuronale Baselines.
- **SHAP:** Methode, die **nachvollziehbar macht**, welche Eingangsgrößen das Modell **wie stark** beeinflussen — nicht nur „schwarze Kiste“.
- **Merkmale im Modell (Auszug, interne Spaltennamen):** u. a. Ölpreisänderung, verzögerte Kern- und Marktpreisänderungen, Abstand zur Marktmitte, Wochentag, Schwankung im Markt — vollständige Liste und Herleitung im [Notebook](https://github.com/felixschrader/dieselpreisprognose/blob/main/notebooks/Machine_Learning_Tagesbasis.ipynb) (`brent_delta2`, `delta_kern_lag1/2`, …).

### Train/Test & Persistenz

- **Trainings- und Testdaten** werden **zeitlich** getrennt (ältere Daten trainieren, neuere testen — **kein** zufälliges Mischen, damit keine Information aus der **Zukunft** ins Training rutscht). Artefakte: `data/ml/` (Modell, Metadaten, Prognose-JSON).

---

## Evaluation

- Kennzahlen aus **Modell-Metadaten** (u. a. **Richtung richtig** im Test, **MAE** = durchschnittlicher absoluter Fehler in der Zielgröße, **R²** = wie viel Varianz das Modell erklärt — Orientierung, **keine** Garantie für Minutenpreise).
- **Baseline Richtung:** Es wird verglichen, ob **Vorzeichen** von Ziel *y* und Vorhersage *ŷ* übereinstimmen (steigt vs. fällt im Sinne der Definition). Die **naive Referenz** „immer null vorhersagen“ entspricht einer Trefferquote = **Anteil der Testtage mit *y* ≤ 0** — **nicht** automatisch 50 %. Viele positive *y* im Test → niedrige Baseline; ausgeglichene Verteilung → Baseline nahe 50 %.
- **Weitere Metriken** (Notebook): z. B. **Korridor** (Richtung stimmt **und** der Fehler bleibt unter einer kleinen Schwelle), Auswertungen nur bei **großem** |*y*| — jeweils **andere** Frage als die reine Vorzeichen-Trefferquote.
- **Dashboard (rückblickend):** „Richtung korrekt“ nutzt eine **±0,5-Cent-Einteilung** — für Leser:innen eingängiger, **nicht dieselbe** Kennzahl wie die strenge Vorzeichen-Metrik im Notebook.

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

| Name | Rolle |
|------|-------|
| [Felix Schrader](https://www.linkedin.com/in/felixschrader/) | Infrastruktur, Data Engineering, ML, Automatisierung |
| [Girandoux Fandio Nganwajop](https://www.linkedin.com/in/girandoux-fandio-08628bb9/) | ETL, EDA, Data Engineering |
| [Ghislain Wamo](https://www.linkedin.com/search/results/all/?keywords=Ghislain%20Wamo) | Datenarchitektur, Dashboard |

*Data Science Institute · Weiterbildung 2026 · Berlin*
