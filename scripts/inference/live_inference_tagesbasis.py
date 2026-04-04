#!/usr/bin/env python3
# live_inference_tagesbasis.py
# Täglich via GitHub Actions: Station ml_master, Ziel K(t+1)−K(t−1).
# Schreibt: data/ml/prognose_tagesbasis.json + data/ml/prognose_log.csv
#
# richtung_korrekt im Log: Vorzeichen wie Notebook (Delta > 0 vs. ≤ 0), nicht SCHWELLE_ANP-3-Klassen.
#
# Kernpreis: p10 der Stundenmedien 13–20 h (wie Notebook).
# Brent/EUR: voller Kalender, ffill/bfill, plus BRENT_CAL_FORWARD_DAYS in die Zukunft
# (kein Handel Sa/So → letzter Kurs bleibt stehen bis zum nächsten Handelstag).

import csv
import json
import os

import joblib
import numpy as np
import pandas as pd
import requests
from datetime import datetime
from dotenv import load_dotenv
import pytz

load_dotenv()
BERLIN = pytz.timezone("Europe/Berlin")
JETZT = datetime.now(BERLIN)
HEUTE = JETZT.date()

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
KERN_STUNDEN = list(range(13, 21))
SCHWELLE_ANP = 0.005

# Kalender bis letzter Kerntag + N Tage (Wochenende/Feiertage ohne neue CSV-Zeilen)
BRENT_CAL_FORWARD_DAYS = 14

MODELL_PATH = "data/ml/modell_rf_ml_master_station_kern_tp1_tm1.pkl"
META_PATH = "data/ml/modell_metadaten_ml_master_station_kern_tp1_tm1.json"
PROGNOSE_PATH = "data/ml/prognose_tagesbasis.json"
LOG_PATH = "data/ml/prognose_log.csv"

BRENT_CSV = "data/brent_futures_daily.csv"
EUR_CSV = "data/eur_usd_rate.csv"
PREISE_PQ = "data/tankstellen_preise.parquet"


def _download_model_if_missing(local_path: str, env_url_key: str) -> bool:
    if os.path.exists(local_path):
        return True
    fname = os.path.basename(local_path)
    candidates = []
    env_url = os.getenv(env_url_key)
    if env_url:
        candidates.append(env_url)
    candidates.append(
        f"https://github.com/felixschrader/dieselpreisprognose/releases/latest/download/{fname}"
    )
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    for url in candidates:
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and r.content:
                with open(local_path, "wb") as f:
                    f.write(r.content)
                print(f"Modell geladen von: {url}")
                return True
            print(f"Kein Modell unter {url} (HTTP {r.status_code})")
        except Exception as e:
            print(f"Download fehlgeschlagen ({url}): {e}")
    return False


def tage_seit(series):
    result, z = [], 0
    for v in series:
        z = 0 if v == 1 else z + 1
        result.append(z)
    return result


def safe(val, fallback=0.0):
    return float(val) if not pd.isna(val) else fallback


def load_brent_eur_calendar(tag_start: pd.Timestamp, tag_end: pd.Timestamp) -> pd.DataFrame:
    """Voller Tageskalender [tag_start, tag_end], Brent/EUR aus CSV, Lücken ffill/bfill."""
    brent = pd.read_csv(BRENT_CSV, parse_dates=["period"]).sort_values("period")
    eur = pd.read_csv(EUR_CSV, parse_dates=["period"]).sort_values("period")
    brent = brent.rename(columns={"period": "tag", "brent_futures_usd": "brent_usd"})
    eur = eur.rename(columns={"period": "tag"})
    m = brent.merge(eur[["tag", "eur_usd"]], on="tag", how="left")
    m["brent_eur"] = m["brent_usd"] / m["eur_usd"]

    kal = pd.DataFrame({"tag": pd.date_range(tag_start.normalize(), tag_end.normalize(), freq="D")})
    out = kal.merge(m[["tag", "brent_eur"]], on="tag", how="left").sort_values("tag")
    out["brent_eur"] = out["brent_eur"].ffill().bfill()
    out["brent_delta1"] = out["brent_eur"].diff(1)
    out["brent_delta2"] = out["brent_eur"].diff(2)
    out["brent_delta3"] = out["brent_eur"].diff(3)
    return out


metadaten = json.load(open(META_PATH, encoding="utf-8"))
FEATURES = metadaten["feature_cols"]

# Vorherige Prognose (wird überschrieben) — für Log-Vergleich mit gleicher Zieldefinition wie Training
prev_prognose = {}
if os.path.exists(PROGNOSE_PATH):
    try:
        with open(PROGNOSE_PATH, encoding="utf-8") as f:
            prev_prognose = json.load(f)
    except Exception:
        prev_prognose = {}

modell = None
if _download_model_if_missing(MODELL_PATH, "MODELL_RF_ML_MASTER_URL"):
    modell = joblib.load(MODELL_PATH)
    print(f"Modell geladen · {len(FEATURES)} Features")
else:
    print(f"Warnung: Modell fehlt ({MODELL_PATH}) — Heuristik-Fallback.")

# --- Kernpreis-Historie (wie Notebook) ---
preise = pd.read_parquet(PREISE_PQ)
preise = preise[(preise["station_uuid"] == STATION_UUID) & preise["diesel"].notna()].copy()
preise["date"] = pd.to_datetime(preise["date"])
preise["stunde_bin"] = preise["date"].dt.floor("h")
preise["stunde_h"] = preise["date"].dt.hour

std_bins = preise.groupby("stunde_bin")["diesel"].median().reset_index()
std_bins["tag"] = pd.to_datetime(std_bins["stunde_bin"].dt.date)
std_bins["stunde_h"] = std_bins["stunde_bin"].dt.hour

kern_hist = (
    std_bins[std_bins["stunde_h"].isin(KERN_STUNDEN)]
    .groupby("tag")["diesel"]
    .quantile(0.10)
    .reset_index()
    .rename(columns={"diesel": "kernpreis_p10"})
    .sort_values("tag")
    .reset_index(drop=True)
)

kern_hist["delta_kern"] = kern_hist["kernpreis_p10"].diff(1)
kern_hist["delta_kern_lag1"] = kern_hist["delta_kern"].shift(1)
kern_hist["delta_kern_lag2"] = kern_hist["delta_kern"].shift(2)
kern_hist["hat_erhoehung"] = (kern_hist["delta_kern"] > SCHWELLE_ANP).astype(int)
kern_hist["hat_senkung"] = (kern_hist["delta_kern"] < -SCHWELLE_ANP).astype(int)
kern_hist["hat_anpassung"] = (kern_hist["delta_kern"].abs() > SCHWELLE_ANP).astype(int)
kern_hist["wochentag"] = kern_hist["tag"].dt.dayofweek
kern_hist["ist_montag"] = (kern_hist["wochentag"] == 0).astype(int)
kern_hist["tage_seit_erhoehung"] = tage_seit(kern_hist["hat_erhoehung"])
kern_hist["tage_seit_senkung"] = tage_seit(kern_hist["hat_senkung"])

letzte_aral = kern_hist.iloc[-1]
prognose_basis_tag = str(pd.Timestamp(letzte_aral["tag"]).date())
kernpreis_heute = float(letzte_aral["kernpreis_p10"])
print(f"Kernpreis: {kernpreis_heute:.3f} € (Tag {prognose_basis_tag})")

# --- Brent auf vollem Kalender (inkl. Zukunft für roll/shift) ---
t_min = pd.Timestamp(kern_hist["tag"].min())
t_max = pd.Timestamp(kern_hist["tag"].max()) + pd.Timedelta(days=BRENT_CAL_FORWARD_DAYS)
brent_tag = load_brent_eur_calendar(t_min, t_max)

df_markt = kern_hist.merge(
    brent_tag[["tag", "brent_eur", "brent_delta1", "brent_delta2", "brent_delta3"]],
    on="tag",
    how="left",
)
df_markt["kern_roll7_std"] = df_markt["kernpreis_p10"].rolling(7, min_periods=2).std()

brent_bei_anp = np.nan
bruck = []
for _, row in df_markt.iterrows():
    if row["hat_anpassung"] == 1 or np.isnan(brent_bei_anp):
        brent_bei_anp = row["brent_eur"]
    bruck.append(row["brent_eur"] - brent_bei_anp if not np.isnan(brent_bei_anp) else 0.0)
df_markt["brent_druck_seit_anpassung"] = bruck

roll3 = df_markt["brent_eur"].rolling(3, min_periods=2).mean()
df_markt["brent_roll_delta_tm1_tm3"] = roll3.shift(1) - roll3.shift(3)

letzte = df_markt.iloc[-1]
feature_dict = {c: safe(letzte[c]) for c in FEATURES}
X_live = pd.DataFrame([feature_dict])[FEATURES]

brent_delta2 = float(letzte["brent_delta2"]) if not pd.isna(letzte["brent_delta2"]) else 0.0
brent_eur = float(letzte["brent_eur"])

if modell is not None:
    pred_delta = float(modell.predict(X_live)[0])
else:
    pred_delta = float(
        np.nanmean(
            [
                feature_dict.get("delta_kern_lag1", 0.0),
                feature_dict.get("delta_kern_lag2", 0.0),
                feature_dict.get("brent_delta2", 0.0),
            ]
        )
    )
    pred_delta = float(np.clip(pred_delta, -0.03, 0.03))
    print(f"Heuristik-Fallback: pred_delta={pred_delta*100:+.2f} ct")

if pred_delta > SCHWELLE_ANP:
    richtung, empfehlung = "steigt", "heute tanken"
elif pred_delta < -SCHWELLE_ANP:
    richtung, empfehlung = "fällt", "übermorgen tanken"
else:
    richtung, empfehlung = "stabil", "flexibel tanken"

print(f"Prognose: {pred_delta*100:+.2f} ct → {richtung}")


def _richtung_positiv_scharf(d: float) -> int:
    """Wie Notebook richtung_accuracy / richtung_f1: Klasse 1 iff Delta > 0, sonst 0."""
    return int(float(d) > 0)


def _index_fuer_basis_tag(df: pd.DataFrame, basis_tag):
    """Integer-Position i: df nach tag sortiert, tag[i] == basis_tag (nur Datum)."""
    tnorm = pd.Timestamp(basis_tag).normalize()
    mask = (pd.to_datetime(df["tag"]).dt.normalize() == tnorm).to_numpy()
    hit = np.flatnonzero(mask)
    if len(hit) != 1:
        return None
    return int(hit[0])


# Log: wie Training — y[i] = kern[i+1] - kern[i-1] auf sortierten Kerntagen (nicht K(t)-K(t-1) kalendertags).
prev_basis = prev_prognose.get("prognose_basis_tag")
prev_pred = prev_prognose.get("predicted_delta")
if prev_basis is not None and prev_pred is not None:
    j = _index_fuer_basis_tag(kern_hist, prev_basis)
    if j is not None and j >= 1 and j < len(kern_hist) - 1:
        actual_delta = float(
            kern_hist.iloc[j + 1]["kernpreis_p10"] - kern_hist.iloc[j - 1]["kernpreis_p10"]
        )
        basis_datum_str = str(pd.Timestamp(prev_basis).date())
        korrekt = int(
            _richtung_positiv_scharf(float(prev_pred)) == _richtung_positiv_scharf(actual_delta)
        )
        log_exists = os.path.exists(LOG_PATH)
        bereits = False
        if log_exists:
            with open(LOG_PATH, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("datum") == basis_datum_str:
                        bereits = True
                        break
        if not bereits:
            with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=["datum", "predicted_delta", "actual_delta", "richtung_korrekt"],
                )
                if not log_exists:
                    w.writeheader()
                w.writerow(
                    {
                        "datum": basis_datum_str,
                        "predicted_delta": round(float(prev_pred), 5),
                        "actual_delta": round(actual_delta, 5),
                        "richtung_korrekt": korrekt,
                    }
                )
            print(
                f"Log: basis_tag={basis_datum_str} (y=K[i+1]-K[i-1]) "
                f"pred={float(prev_pred)*100:+.2f}ct actual={actual_delta*100:+.2f}ct ok={korrekt}"
            )
        else:
            print(f"Log: basis_tag={basis_datum_str} bereits vorhanden")
    else:
        print(
            f"Log: noch kein Ist für Prognose vom {prev_basis} "
            f"(warte auf nächsten Kerntag nach i+1 in der Zeitreihe)"
        )
else:
    print("Log: keine vorherige prognose_basis_tag/predicted_delta in JSON (erster Lauf oder Altstand)")

horizont = metadaten.get("horizont", "2 Tage")
prognose_json = {
    "datum": str(HEUTE),
    "timestamp": JETZT.strftime("%Y-%m-%d %H:%M"),
    "station_uuid": STATION_UUID,
    "station": metadaten.get("station", "ARAL Dürener Str. 407"),
    "kernpreis_aktuell": round(kernpreis_heute, 3),
    "ziel_modell": "K[i+1] - K[i-1] (sortierte Kerntage, wie shift im Notebook)",
    "prognose_basis_tag": prognose_basis_tag,
    "markt_median": None,
    "residuum_heute": None,
    "predicted_delta": round(pred_delta, 5),
    "predicted_delta_cent": round(pred_delta * 100, 2),
    "richtung": richtung,
    "empfehlung": empfehlung,
    "begruendung": (
        f"ML ml_master · {horizont}: {pred_delta*100:+.1f} ct "
        f"(Brent €/bbl {brent_eur:.1f}, Δ2 {brent_delta2:+.3f})"
    ),
    "brent_eur": round(brent_eur, 2),
    "brent_delta2": round(brent_delta2, 4),
    "brent_kalender_ffill_bis": str(t_max.date()),
    "tage_seit_erhoehung": int(letzte_aral["tage_seit_erhoehung"]),
    "tage_seit_senkung": int(letzte_aral["tage_seit_senkung"]),
    "nrw_stationen_live": None,
    "modell": metadaten["modell"] if modell is not None else "fallback_heuristik_ohne_pkl",
    "modell_pfad": MODELL_PATH,
    "richtung_accuracy_test": metadaten.get("richtung_accuracy_test"),
    "horizont": horizont,
    "baseline_richtung_test": metadaten.get("baseline_richtung_test"),
    "delta_richtung_ueber_baseline_pp": metadaten.get("delta_ueber_baseline"),
    "baseline_richtung_interpretation": metadaten.get("baseline_richtung_interpretation"),
}

with open(PROGNOSE_PATH, "w", encoding="utf-8") as f:
    json.dump(prognose_json, f, indent=2, ensure_ascii=False)

print(f"\nGespeichert: {PROGNOSE_PATH}")
print(json.dumps(prognose_json, indent=2, ensure_ascii=False))
