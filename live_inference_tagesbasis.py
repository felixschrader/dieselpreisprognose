#!/usr/bin/env python3
# live_inference_tagesbasis.py
# Täglich ausgeführt via GitHub Actions.
# Berechnet den Tages-Kernpreis (p10, Stunden 13–20 Uhr),
# baut den Feature-Vektor und schreibt eine 3-Tage-Prognose als JSON.

import pandas as pd
import numpy as np
import joblib
import json
import requests
import os
from datetime import datetime, timedelta
from scipy.stats import linregress
from dotenv import load_dotenv
import pytz

load_dotenv()
TANKERKOENIG_KEY = os.getenv("TANKERKOENIG_KEY")

BERLIN       = pytz.timezone("Europe/Berlin")
HEUTE        = datetime.now(BERLIN).date()
STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
KERN_STUNDEN = list(range(13, 21))  # 13–20 Uhr

# --- Schritt 1: Metadaten laden ---
metadaten    = json.load(open("data/ml/modell_metadaten_tagesbasis_aral_duerener.json"))
feature_cols = metadaten["feature_cols"]
nachbar_uuids = metadaten.get("nachbar_uuids", [])

# --- Schritt 2: Historische Preisdaten laden ---
preise = pd.read_parquet("data/tankstellen_preise.parquet")
preise["date"] = pd.to_datetime(preise["date"])
preise = preise[preise["diesel"].notna()].copy()

# ARAL isolieren
aral = preise[preise["station_uuid"] == STATION_UUID].copy()
aral["tag"]     = pd.to_datetime(aral["date"].dt.date)
aral["stunde_h"] = aral["date"].dt.hour
aral["stunde_bin"] = aral["date"].dt.floor("h")

# Stundenbins als Median
aral_std = (
    aral.groupby("stunde_bin")["diesel"]
    .median()
    .reset_index()
)
aral_std["tag"]     = pd.to_datetime(aral_std["stunde_bin"].dt.date)
aral_std["stunde_h"] = aral_std["stunde_bin"].dt.hour

# --- Schritt 3: Kernpreis heute (p10 Kernstunden) ---
heute_kern = aral_std[
    (aral_std["tag"] == pd.Timestamp(HEUTE)) &
    (aral_std["stunde_h"].isin(KERN_STUNDEN))
]["diesel"]

if len(heute_kern) >= 2:
    kernpreis_heute = float(heute_kern.quantile(0.10))
else:
    # Fallback: letzter bekannter Preis
    kernpreis_heute = float(aral_std.sort_values("stunde_bin")["diesel"].iloc[-1])
    print(f"Warnung: Wenige Kernstunden heute ({len(heute_kern)}) — Fallback auf letzten Preis")

print(f"Kernpreis heute: {kernpreis_heute:.3f} €")

# --- Schritt 4: Tages-Kernpreise der letzten 30 Tage ---
cutoff = pd.Timestamp(HEUTE) - pd.Timedelta(days=30)
kern_hist = (
    aral_std[
        (aral_std["tag"] >= cutoff) &
        (aral_std["stunde_h"].isin(KERN_STUNDEN))
    ]
    .groupby("tag")["diesel"]
    .quantile(0.10)
    .reset_index()
    .rename(columns={"diesel": "kernpreis"})
    .sort_values("tag")
)

# Heute anhängen
heute_row = pd.DataFrame({"tag": [pd.Timestamp(HEUTE)], "kernpreis": [kernpreis_heute]})
kern_hist = pd.concat([kern_hist, heute_row]).drop_duplicates("tag").sort_values("tag").reset_index(drop=True)

# --- Schritt 5: delta_t0 (heute vs. gestern) ---
if len(kern_hist) >= 2:
    delta_t0      = float(kern_hist["kernpreis"].iloc[-1] - kern_hist["kernpreis"].iloc[-2])
    delta_t0_lag1 = float(kern_hist["kernpreis"].iloc[-2] - kern_hist["kernpreis"].iloc[-3]) if len(kern_hist) >= 3 else 0.0
    delta_t0_lag2 = float(kern_hist["kernpreis"].iloc[-3] - kern_hist["kernpreis"].iloc[-4]) if len(kern_hist) >= 4 else 0.0
else:
    delta_t0 = delta_t0_lag1 = delta_t0_lag2 = 0.0

kernpreis_std7d = float(kern_hist["kernpreis"].tail(7).std()) if len(kern_hist) >= 3 else 0.0

# --- Schritt 6: Externe Features ---
brent   = pd.read_csv("data/brent_futures_daily.csv",  parse_dates=["period"]).sort_values("period")
eur_usd = pd.read_csv("data/eur_usd_rate.csv",         parse_dates=["period"]).sort_values("period")

brent_usd      = float(brent["brent_futures_usd"].iloc[-1])
brent_usd_t1   = float(brent["brent_futures_usd"].iloc[-2])
brent_usd_t2   = float(brent["brent_futures_usd"].iloc[-3])
eur_usd_val    = float(eur_usd["eur_usd"].iloc[-1])
eur_usd_t1     = float(eur_usd["eur_usd"].iloc[-2])
eur_usd_t2     = float(eur_usd["eur_usd"].iloc[-3])
eur_usd_t3     = float(eur_usd["eur_usd"].iloc[-4])

brent_eur_heute = brent_usd / eur_usd_val
brent_eur_t1    = brent_usd_t1 / eur_usd_t1
brent_eur_t2    = brent_usd_t2 / eur_usd_t2

brent_eur_delta1 = brent_eur_heute - brent_eur_t1
brent_eur_delta2 = brent_eur_t1    - brent_eur_t2

# --- Schritt 7: Nachbar-Features ---
nachbarn = preise[preise["station_uuid"].isin(nachbar_uuids)].copy()
nachbarn["tag"]     = pd.to_datetime(nachbarn["date"].dt.date)
nachbarn["stunde_h"] = nachbarn["date"].dt.hour
nachbarn["stunde_bin"] = nachbarn["date"].dt.floor("h")

nachbarn_std = (
    nachbarn.groupby(["station_uuid", "stunde_bin"])["diesel"]
    .median()
    .reset_index()
)
nachbarn_std["tag"]     = pd.to_datetime(nachbarn_std["stunde_bin"].dt.date)
nachbarn_std["stunde_h"] = nachbarn_std["stunde_bin"].dt.hour

nachbarn_kern_heute = nachbarn_std[
    (nachbarn_std["tag"] == pd.Timestamp(HEUTE)) &
    (nachbarn_std["stunde_h"].isin(KERN_STUNDEN))
]["diesel"]

if len(nachbarn_kern_heute) > 0:
    nachbar_p10_kern = float(nachbarn_kern_heute.quantile(0.10))
else:
    # Fallback: letzter bekannter Nachbar-Kernpreis
    nachbar_p10_kern = kernpreis_heute

delta_zu_nachbarn = kernpreis_heute - nachbar_p10_kern

# Lags delta_zu_nachbarn
nachbarn_kern_hist = (
    nachbarn_std[nachbarn_std["stunde_h"].isin(KERN_STUNDEN)]
    .groupby("tag")["diesel"]
    .quantile(0.10)
    .reset_index()
    .rename(columns={"diesel": "nachbar_kern"})
    .sort_values("tag")
)
aral_kern_merge = kern_hist.merge(nachbarn_kern_hist, on="tag", how="left")
aral_kern_merge["delta_zu_nachbarn"] = aral_kern_merge["kernpreis"] - aral_kern_merge["nachbar_kern"]

delta_zu_nachbarn_lag1 = float(aral_kern_merge["delta_zu_nachbarn"].iloc[-2]) if len(aral_kern_merge) >= 2 else 0.0
delta_zu_nachbarn_lag2 = float(aral_kern_merge["delta_zu_nachbarn"].iloc[-3]) if len(aral_kern_merge) >= 3 else 0.0

# --- Schritt 8: Externe Effekte ---
extern  = pd.read_csv("data/externe_effekte.csv", parse_dates=["date"])
heute_str = str(HEUTE)
ext_heute = extern[extern["date"].dt.strftime("%Y-%m-%d") == heute_str]
ist_niedrigwasser = int(ext_heute["ist_niedrigwasser"].values[0]) if len(ext_heute) > 0 else 0

schulferien = pd.read_csv("data/schulferien.csv")
schulferien = schulferien[schulferien["bundesland_code"] == "DE-NW"].copy()
schulferien["datum_start"] = pd.to_datetime(schulferien["datum_start"])
schulferien["datum_ende"]  = pd.to_datetime(schulferien["datum_ende"])
ist_schulferien_t1 = int(any(
    row["datum_start"].date() <= (HEUTE + timedelta(days=1)) <= row["datum_ende"].date()
    for _, row in schulferien.iterrows()
))

# --- Schritt 9: Feature-Vektor ---
feature_dict = {
    "brent_usd":             brent_usd,
    "eur_usd":               eur_usd_val,
    "eur_usd_t1":            eur_usd_t1,
    "eur_usd_t2":            eur_usd_t2,
    "eur_usd_t3":            eur_usd_t3,
    "delta_t0":              delta_t0,
    "kernpreis_std7d":       kernpreis_std7d,
    "delta_t0_lag1":         delta_t0_lag1,
    "delta_t0_lag2":         delta_t0_lag2,
    "brent_eur_delta1":      brent_eur_delta1,
    "brent_eur_delta2":      brent_eur_delta2,
    "ist_schulferien_t1":    ist_schulferien_t1,
    "ist_niedrigwasser":     ist_niedrigwasser,
    "delta_zu_nachbarn":     delta_zu_nachbarn,
    "delta_zu_nachbarn_lag1": delta_zu_nachbarn_lag1,
    "delta_zu_nachbarn_lag2": delta_zu_nachbarn_lag2,
}

X_live = pd.DataFrame([feature_dict])[feature_cols]

# --- Schritt 10: Prognose ---
modell       = joblib.load("data/ml/modell_rf_tagesbasis_aral_duerener.pkl")
delta_pred   = float(modell.predict(X_live)[0])

# Prognose-Kurve: Kernpreis + kumulatives Delta über 3 Tage
prognose_tage = []
for t in range(1, 4):
    tag_ts   = pd.Timestamp(HEUTE) + pd.Timedelta(days=t)
    preis_erwartet = round(kernpreis_heute + delta_pred * t, 3)
    prognose_tage.append({
        "tag_offset":      t,
        "datum":           tag_ts.strftime("%Y-%m-%d"),
        "delta_erwartet":  round(delta_pred, 4),
        "preis_erwartet":  preis_erwartet,
        "richtung":        "steigt" if delta_pred > 0 else "fällt" if delta_pred < 0 else "stabil",
    })

# --- Schritt 11: Empfehlung ---
if delta_pred < -0.005:
    empfehlung  = "später tanken"
    begruendung = "Kernpreis fällt in den nächsten Tagen — noch etwas warten"
elif delta_pred > 0.005:
    empfehlung  = "heute tanken"
    begruendung = "Kernpreis steigt in den nächsten Tagen — jetzt günstiger"
else:
    empfehlung  = "kein klarer Vorteil"
    begruendung = "Kernpreis bleibt stabil — kein Timing-Vorteil"

# Nachbar-Vergleich
dip_oder_peak = "Dip" if delta_zu_nachbarn < 0 else "Peak"

# --- Schritt 12: Brent-Trend (letzte 7 Tage) ---
brent_7d = brent.tail(7)["brent_futures_usd"].values
x_trend  = np.arange(len(brent_7d)).astype(float)
slope, _, r, _, _ = linregress(x_trend, brent_7d.astype(float))
brent_trend = "steigt" if slope > 0.1 else "fällt" if slope < -0.1 else "seitwärts"

# --- Schritt 13: JSON speichern ---
prognose = {
    "timestamp":           datetime.now(BERLIN).strftime("%Y-%m-%d %H:%M"),
    "datum_heute":         str(HEUTE),
    "station_uuid":        STATION_UUID,
    "station":             "ARAL Dürener Str. 407",
    "kernpreis_heute":     round(kernpreis_heute, 3),
    "nachbar_p10_kern":    round(nachbar_p10_kern, 3),
    "delta_zu_nachbarn":   round(delta_zu_nachbarn, 4),
    "dip_oder_peak":       dip_oder_peak,
    "delta_prognose":      round(delta_pred, 4),
    "richtung":            prognose_tage[0]["richtung"],
    "empfehlung":          empfehlung,
    "begruendung":         begruendung,
    "brent_aktuell":       round(brent_usd, 2),
    "brent_eur_aktuell":   round(brent_eur_heute, 2),
    "brent_eur_delta1":    round(brent_eur_delta1, 4),
    "brent_eur_delta2":    round(brent_eur_delta2, 4),
    "brent_trend_7d":      brent_trend,
    "eur_usd_aktuell":     round(eur_usd_val, 4),
    "prognose_tage":       prognose_tage,
    "modell_richtung_accuracy_test": metadaten["richtung_accuracy_test"],
    "modell_korridor_test":          metadaten["korridor_accuracy_test"],
    "shap_top5":           metadaten.get("shap_top5", []),
}

with open("data/ml/prognose_tagesbasis.json", "w", encoding="utf-8") as f:
    json.dump(prognose, f, indent=2, ensure_ascii=False)

print(json.dumps(prognose, indent=2, ensure_ascii=False))
