#!/usr/bin/env python3
# backfill_prognose_log.py
# Einmalig: fehlende Tage in prognose_log.csv nachberechnen.
# Rekonstruiert Feature-Vektor für jeden fehlenden Tag und trägt
# predicted_delta + actual_delta + richtung_korrekt ein.

import pandas as pd
import numpy as np
import joblib, json, os, csv
from datetime import date, timedelta

STATION_UUID  = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
KERN_STUNDEN  = list(range(13, 21))
SCHWELLE_ANP  = 0.005
MODELL_PATH   = "data/ml/modell_rf_markt_aral_duerener.pkl"
META_PATH     = "data/ml/modell_metadaten_markt_aral_duerener.json"
LOG_PATH      = "data/ml/prognose_log.csv"

modell    = joblib.load(MODELL_PATH)
metadaten = json.load(open(META_PATH, encoding="utf-8"))
FEATURES  = metadaten["feature_cols"]

# --- Kernpreis-Zeitreihe aufbauen ---
preise = pd.read_parquet("data/tankstellen_preise.parquet")
preise = preise[(preise["station_uuid"] == STATION_UUID) & preise["diesel"].notna()].copy()
preise["date"]       = pd.to_datetime(preise["date"])
preise["stunde_bin"] = preise["date"].dt.floor("h")
preise["stunde_h"]   = preise["date"].dt.hour

std_bins = preise.groupby("stunde_bin")["diesel"].median().reset_index()
std_bins["tag"]      = pd.to_datetime(std_bins["stunde_bin"].dt.date)
std_bins["stunde_h"] = std_bins["stunde_bin"].dt.hour

kern_hist = (
    std_bins[std_bins["stunde_h"].isin(KERN_STUNDEN)]
    .groupby("tag")["diesel"].quantile(0.10)
    .reset_index().rename(columns={"diesel": "kernpreis_p10"})
    .sort_values("tag").reset_index(drop=True)
)
kern_hist["delta_kern"]      = kern_hist["kernpreis_p10"].diff(1)
kern_hist["delta_kern_lag1"] = kern_hist["delta_kern"].shift(1)
kern_hist["delta_kern_lag2"] = kern_hist["delta_kern"].shift(2)
kern_hist["hat_erhoehung"]   = (kern_hist["delta_kern"] >  SCHWELLE_ANP).astype(int)
kern_hist["hat_senkung"]     = (kern_hist["delta_kern"] < -SCHWELLE_ANP).astype(int)
kern_hist["wochentag"]       = kern_hist["tag"].dt.dayofweek
kern_hist["ist_montag"]      = (kern_hist["wochentag"] == 0).astype(int)

def tage_seit(series):
    result, z = [], 0
    for v in series:
        z = 0 if v == 1 else z + 1
        result.append(z)
    return result

kern_hist["tage_seit_erhoehung"] = tage_seit(kern_hist["hat_erhoehung"])
kern_hist["tage_seit_senkung"]   = tage_seit(kern_hist["hat_senkung"])
kern_hist = kern_hist.set_index("tag")

# --- Markt-Zeitreihe aufbauen ---
df_nrw = pd.read_parquet("data/ml/aral_nrw_tagesbasis.parquet")
df_nrw["tag"] = pd.to_datetime(df_nrw["tag"])
markt_serie = (
    df_nrw.groupby("tag")["kernpreis_p10"].median()
    .reset_index().rename(columns={"kernpreis_p10": "markt_median"})
    .sort_values("tag")
)
markt_serie["delta_markt"]      = markt_serie["markt_median"].diff(1)
markt_serie["delta_markt_lag1"] = markt_serie["delta_markt"].shift(1)
markt_serie["delta_markt_lag2"] = markt_serie["delta_markt"].shift(2)
markt_serie["markt_std"]        = markt_serie["markt_median"].rolling(7, min_periods=2).std()
markt_serie = markt_serie.set_index("tag")

# Residuum
res_df = kern_hist[["kernpreis_p10"]].join(markt_serie[["markt_median"]], how="left")
res_df["residuum"]      = res_df["kernpreis_p10"] - res_df["markt_median"]
res_df["residuum_lag1"] = res_df["residuum"].shift(1)

# --- Brent ---
brent   = pd.read_csv("data/brent_futures_daily.csv", parse_dates=["period"]).sort_values("period")
eur_usd = pd.read_csv("data/eur_usd_rate.csv",        parse_dates=["period"]).sort_values("period")
brent   = brent.rename(columns={"period": "tag", "brent_futures_usd": "brent_usd"})
eur_usd = eur_usd.rename(columns={"period": "tag"})
brent_tag = brent.merge(eur_usd, on="tag", how="left")
brent_tag["brent_eur"]    = brent_tag["brent_usd"] / brent_tag["eur_usd"]
brent_tag["brent_delta2"] = brent_tag["brent_eur"].diff(2)
brent_tag = brent_tag.set_index("tag")

# --- Fehlende Tage bestimmen ---
log_df = pd.read_csv(LOG_PATH, parse_dates=["datum"])
vorhandene = set(log_df["datum"].dt.date)

gestern   = date.today() - timedelta(days=1)
alle_tage = pd.date_range(log_df["datum"].min(), gestern).date
fehlende  = sorted([d for d in alle_tage if d not in vorhandene])
print(f"Fehlende Tage: {len(fehlende)}")
for d in fehlende:
    print(f"  {d}")

# --- Richtungsklasse ---
def richtung_klasse(d):
    if d > SCHWELLE_ANP:  return 1
    if d < -SCHWELLE_ANP: return -1
    return 0

def safe(val, fallback=0.0):
    return float(val) if not pd.isna(val) else fallback

# --- Backfill ---
neue_zeilen = []

for tag in fehlende:
    tag_ts   = pd.Timestamp(tag)
    tag_prev = pd.Timestamp(tag - timedelta(days=1))

    # Kernpreis für diesen Tag und Vortag nötig für actual_delta
    if tag_ts not in kern_hist.index or tag_prev not in kern_hist.index:
        print(f"  {tag}: Kernpreis fehlt — übersprungen")
        continue

    # Features: alles was das Modell zum Zeitpunkt tag_prev kennt (shift=2 → lag auf tag-1)
    aral = kern_hist.loc[tag_prev] if tag_prev in kern_hist.index else None
    if aral is None:
        print(f"  {tag}: Feature-Tag fehlt — übersprungen")
        continue

    markt = markt_serie.loc[tag_prev] if tag_prev in markt_serie.index else None
    res   = res_df.loc[tag_prev]      if tag_prev in res_df.index      else None

    # Brent: letzter verfügbarer Handelstag vor tag_prev
    brent_sub = brent_tag[brent_tag.index <= tag_prev].dropna(subset=["brent_delta2"])
    if brent_sub.empty:
        print(f"  {tag}: Brent fehlt — übersprungen")
        continue
    brent_row = brent_sub.iloc[-1]

    feature_dict = {
        "brent_delta2":        float(brent_row["brent_delta2"]),
        "delta_kern_lag1":     safe(aral["delta_kern_lag1"]),
        "delta_kern_lag2":     safe(aral["delta_kern_lag2"]),
        "delta_markt_lag1":    safe(markt["delta_markt_lag1"]) if markt is not None else 0.0,
        "delta_markt_lag2":    safe(markt["delta_markt_lag2"]) if markt is not None else 0.0,
        "residuum_lag1":       safe(res["residuum_lag1"])       if res   is not None else 0.0,
        "tage_seit_erhoehung": float(aral["tage_seit_erhoehung"]),
        "tage_seit_senkung":   float(aral["tage_seit_senkung"]),
        "wochentag":           float(aral["wochentag"]),
        "ist_montag":          float(aral["ist_montag"]),
        "markt_std":           safe(markt["markt_std"]) if markt is not None else 0.0,
    }

    X_live     = pd.DataFrame([feature_dict])[FEATURES]
    pred_delta = float(modell.predict(X_live)[0])

    actual_delta = float(kern_hist.loc[tag_ts, "kernpreis_p10"]) - float(kern_hist.loc[tag_prev, "kernpreis_p10"])
    korrekt      = int(richtung_klasse(pred_delta) == richtung_klasse(actual_delta))

    neue_zeilen.append({
        "datum":            str(tag),
        "predicted_delta":  round(pred_delta,   5),
        "actual_delta":     round(actual_delta, 5),
        "richtung_korrekt": korrekt,
    })
    print(f"  {tag}: pred={pred_delta*100:+.2f}ct actual={actual_delta*100:+.2f}ct korrekt={korrekt}")

# --- In Log schreiben ---
if neue_zeilen:
    log_df_neu = pd.concat([
        log_df,
        pd.DataFrame(neue_zeilen)
    ], ignore_index=True)
    log_df_neu["datum"] = pd.to_datetime(log_df_neu["datum"])
    log_df_neu = log_df_neu.sort_values("datum").reset_index(drop=True)
    log_df_neu["datum"] = log_df_neu["datum"].dt.date
    log_df_neu.to_csv(LOG_PATH, index=False)
    print(f"\nFertig: {len(neue_zeilen)} Einträge hinzugefügt → {LOG_PATH}")
else:
    print("\nKeine neuen Einträge.")
