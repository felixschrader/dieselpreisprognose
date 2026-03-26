# dashboard.py
# Streamlit Dashboard — Spritpreisprognose ARAL Dürener Str. 407
# Läuft auf Streamlit Cloud, liest prognose_aktuell.json aus dem Repo

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime
import pytz

# =========================================
# Konfiguration
# =========================================
st.set_page_config(
    page_title="Dieselpreis Köln · ARAL Dürener Str.",
    page_icon="⛽",
    layout="centered"
)

# Corporate Design — Injiziertes CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Hintergrund */
.stApp {
    background-color: #F4F6F9;
}

/* Hauptcontainer */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 780px;
}

/* Trennlinien */
hr {
    border-color: #DDE1E8;
    margin: 1.5rem 0;
}

/* Metriken-Karten */
.metric-card {
    background: #FFFFFF;
    border: 1px solid #DDE1E8;
    border-radius: 10px;
    padding: 18px 20px;
    height: 100%;
}
.metric-label {
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8892A0;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 2.1rem;
    font-weight: 600;
    color: #1A2332;
    line-height: 1.1;
    font-family: 'DM Mono', monospace;
}
.metric-delta {
    font-size: 0.8rem;
    font-weight: 500;
    margin-top: 4px;
}
.delta-neg { color: #1E7E4A; }
.delta-pos { color: #C0392B; }
.delta-neutral { color: #8892A0; }

/* Empfehlungs-Box */
.empfehlung-box {
    border-radius: 10px;
    padding: 20px 24px;
    margin-bottom: 6px;
    border-left: 4px solid;
}
.empfehlung-heute {
    background: #EBF5EE;
    border-left-color: #1E7E4A;
}
.empfehlung-morgen {
    background: #FEF9EC;
    border-left-color: #D4A017;
}
.empfehlung-warten {
    background: #FDEDEC;
    border-left-color: #C0392B;
}
.empfehlung-text {
    font-size: 0.97rem;
    color: #2C3E50;
    line-height: 1.6;
}

/* Footer */
.footer-text {
    font-size: 0.72rem;
    color: #A0AAB4;
    line-height: 1.7;
}
.footer-text a {
    color: #6B7A8D;
    text-decoration: none;
}
.footer-text a:hover {
    text-decoration: underline;
}

/* Disclaimer */
.disclaimer {
    font-size: 0.72rem;
    color: #A0AAB4;
    margin-top: 6px;
}
.disclaimer a {
    color: #6B7A8D;
}
</style>
""", unsafe_allow_html=True)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
JSON_URL     = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/prognose_aktuell.json"
PARQUET_URL  = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/tankstellen_preise.parquet"
LOG_URL      = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/preis_live_log.csv"
BERLIN       = pytz.timezone("Europe/Berlin")

# =========================================
# Daten laden
# =========================================
@st.cache_data(ttl=300)
def lade_prognose():
    r = requests.get(JSON_URL)
    return r.json()

@st.cache_data(ttl=300)
def lade_preisverlauf():
    df = pd.read_parquet(PARQUET_URL)
    df = df[df["station_uuid"] == STATION_UUID].copy()
    df = df[df["diesel"].notna()].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df = df.rename(columns={"date": "stunde", "diesel": "preis"})
    return df[["stunde", "preis"]]

@st.cache_data(ttl=60)
def lade_live_log():
    try:
        df = pd.read_csv(LOG_URL, parse_dates=["timestamp"], on_bad_lines="skip")
        return df
    except:
        return pd.DataFrame(columns=["timestamp", "preis", "tendenz_24h"])

@st.cache_data(ttl=60)
def lade_aktueller_preis():
    try:
        key = st.secrets["TANKERKOENIG_KEY"]
        url = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={STATION_UUID}&apikey={key}"
        r   = requests.get(url, timeout=5)
        d   = r.json()
        return float(d["prices"][STATION_UUID]["diesel"])
    except:
        return None

@st.cache_data(ttl=3600)
def generiere_empfehlung(preis, mean_24h, richtung, delta, empfehlung, begruendung, signal_rausch):
    prompt = f"""Du bist ein hilfreicher Tankstellen-Assistent für normale Autofahrer. Schreibe 2-3 Sätze auf Deutsch.

Fakten:
- Aktueller Dieselpreis: {preis:.3f} € ({preis - mean_24h:+.3f} € vs. 24h-Schnitt)
- Preistrend nächste 24h: {richtung} um ca. {abs(delta):.3f} €
- Verhältnis erwartete Änderung zu typischen Schwankungen: {signal_rausch:.2f} (unter 0.5 = Änderung geht im Rauschen unter, über 1.0 = klares Signal)
- Empfehlung: {empfehlung}

Regeln:
- Erster Satz fett mit **: klare Handlungsempfehlung
- Wenn Signal-Rausch unter 0.5: weise darauf hin dass die erwartete Änderung so klein ist, dass sie durch normale Preisschwankungen aufgehoben werden könnte
- Wenn Signal-Rausch über 1.0: klares Signal, selbstbewusst formulieren
- Kein Fachjargon, keine Zeitangaben über 24h, vorsichtig formulieren"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": st.secrets["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=10
    )
    return r.json()["content"][0]["text"]

# =========================================
# Daten zusammenführen
# =========================================
prognose    = lade_prognose()
df_ext      = lade_preisverlauf()
df_live_raw = lade_live_log()
preis_live  = lade_aktueller_preis()

# Live-Log aufbereiten — volle Auflösung
if not df_live_raw.empty and "timestamp" in df_live_raw.columns:
    df_live = df_live_raw[["timestamp", "preis"]].copy()
    df_live = df_live.rename(columns={"timestamp": "stunde"})
    df_live["stunde"] = pd.to_datetime(df_live["stunde"])
    df_live = df_live.sort_values("stunde").drop_duplicates("stunde").reset_index(drop=True)
else:
    df_live = pd.DataFrame(columns=["stunde", "preis"])

# Gebinnt für 24h-Mittel
if not df_live.empty:
    df_live_binned = df_live.copy()
    df_live_binned["stunde"] = df_live_binned["stunde"].dt.floor("3h")
    df_live_binned = df_live_binned.groupby("stunde").agg(preis=("preis", "last")).reset_index()
    df_ext = (
        pd.concat([df_ext, df_live_binned])
        .drop_duplicates("stunde", keep="last")
        .sort_values("stunde")
        .reset_index(drop=True)
    )

# Zeitstempel
jetzt_ts      = pd.Timestamp(datetime.now(BERLIN)).tz_localize(None)
letzter_preis = preis_live if preis_live else float(prognose["preis_aktuell"])
uhrzeit       = jetzt_ts.strftime("%H:%M")

# Prognose
delta_erwartet = float(prognose["delta_erwartet"])
if prognose["richtung_24h"] == "fällt":
    delta_erwartet = -abs(delta_erwartet)
else:
    delta_erwartet = abs(delta_erwartet)

prognose_preis = letzter_preis + delta_erwartet
prognose_ende  = jetzt_ts + pd.Timedelta(hours=24)

# Plot-Daten
cutoff_7d = jetzt_ts - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

# Graue Linie: Parquet + Live-Log + aktueller Punkt
df_hist = pd.concat([
    df_plot[["stunde", "preis"]],
    df_live[df_live["stunde"] >= cutoff_7d][["stunde", "preis"]] if not df_live.empty else pd.DataFrame(columns=["stunde", "preis"]),
    pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
]).sort_values("stunde").drop_duplicates("stunde", keep="last").reset_index(drop=True)

# Rollierende 24h-Bins
bin_grenzen = [jetzt_ts - pd.Timedelta(hours=24 * i) for i in range(8, -1, -1)]
df_24h_rows = []
for i in range(len(bin_grenzen) - 1):
    start = bin_grenzen[i]
    ende  = bin_grenzen[i + 1]
    mask  = (df_hist["stunde"] >= start) & (df_hist["stunde"] < ende)
    if mask.sum() > 0:
        df_24h_rows.append({"stunde": start, "preis": df_hist.loc[mask, "preis"].mean()})

df_24h = pd.DataFrame(df_24h_rows).sort_values("stunde").reset_index(drop=True)
if not df_24h.empty:
    df_24h = pd.concat([
        df_24h,
        pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
    ]).reset_index(drop=True)

mean_24h = float(df_hist[df_hist["stunde"] >= (jetzt_ts - pd.Timedelta(hours=24))]["preis"].mean())

# Evaluation
eval_text = None
if not df_live_raw.empty and "tendenz_24h" in df_live_raw.columns:
    df_live_raw["timestamp"] = pd.to_datetime(df_live_raw["timestamp"])
    ziel_ts  = jetzt_ts - pd.Timedelta(hours=24)
    toleranz = pd.Timedelta(minutes=30)
    df_t24   = df_live_raw[
        (df_live_raw["timestamp"] >= ziel_ts - toleranz) &
        (df_live_raw["timestamp"] <= ziel_ts + toleranz)
    ]
    if not df_t24.empty and not pd.isna(df_t24.iloc[-1]["tendenz_24h"]):
        eval_diff = letzter_preis - (float(df_t24.iloc[-1]["preis"]) + float(df_t24.iloc[-1]["tendenz_24h"]))
        eval_text = f"Eval: {eval_diff:+.3f} €"

# Signal-Rausch
signal_rausch = abs(delta_erwartet) / float(prognose["volatilitaet_7d"]) if float(prognose["volatilitaet_7d"]) > 0 else 0

# KI-Text
try:
    ki_text = generiere_empfehlung(
        letzter_preis, mean_24h,
        prognose["richtung_24h"], delta_erwartet,
        prognose["empfehlung"], prognose["begruendung"],
        signal_rausch
    )
except:
    ki_text = f"**{prognose['empfehlung'].capitalize()}.** {prognose['begruendung']}"

# =========================================
# Hilfsfunktionen
# =========================================
def preis_fmt(p):
    s = f"{p:.3f}"
    return f"{s[:-1]}<sup style='font-size:0.55em; vertical-align:super;'>{s[-1]}</sup>"

# =========================================
# Header
# =========================================
st.markdown(f"""
<div style='margin-bottom: 1.5rem;'>
    <div style='font-size: 1.6rem; font-weight: 600; color: #1A2332; letter-spacing: -0.02em;'>
        ⛽ Dieselpreis-Prognose
    </div>
    <div style='font-size: 0.8rem; color: #8892A0; margin-top: 3px;'>
        ARAL Dürener Str. 407, Köln &nbsp;·&nbsp; Stand: {uhrzeit} Uhr
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# =========================================
# Metriken — 3 Spalten
# =========================================
delta_val   = letzter_preis - mean_24h
delta_class = "delta-neg" if delta_val < 0 else "delta-pos"
delta_str   = f"{delta_val:+.2f} € vs. Ø 24h"

tendenz_pfeil = "↓" if prognose["richtung_24h"] == "fällt" else "↑"
tendenz_farbe = "#1E7E4A" if prognose["richtung_24h"] == "fällt" else "#C0392B"

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Ø letzte 24h</div>
        <div class='metric-value'>{preis_fmt(mean_24h)} €</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Aktueller Preis · {uhrzeit} Uhr</div>
        <div class='metric-value'>{preis_fmt(letzter_preis)} €</div>
        <div class='metric-delta {delta_class}'>{delta_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    eval_html = f"<div class='metric-delta delta-neutral'>{eval_text}</div>" if eval_text else ""
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Tendenz nächste 24h</div>
        <div class='metric-value' style='color:{tendenz_farbe};'>{tendenz_pfeil}</div>
        {eval_html}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

# =========================================
# KI-Empfehlung
# =========================================
if "heute" in prognose["empfehlung"]:
    box_class = "empfehlung-heute"
elif "morgen" in prognose["empfehlung"]:
    box_class = "empfehlung-morgen"
else:
    box_class = "empfehlung-warten"

ki_html = ki_text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

st.markdown(f"""
<div class='empfehlung-box {box_class}'>
    <div class='empfehlung-text'>{ki_html}</div>
</div>
<div class='disclaimer'>
    ℹ️ KI-generierter Text · <a href='https://www.anthropic.com' target='_blank'>Claude API (Anthropic)</a> ·
    Modell: XGBoost · Trainingsgenauigkeit: {prognose['modell_accuracy']:.1f}% ·
    Prognosen sind Wahrscheinlichkeiten, keine Garantien.
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# =========================================
# Preisverlauf
# =========================================
st.markdown("<div style='font-size:1.05rem; font-weight:600; color:#1A2332; margin-bottom:0.75rem;'>Preisverlauf — letzte 7 Tage + Prognose 24h</div>", unsafe_allow_html=True)

fig = go.Figure()

# Historische Linie — hellgrau
fig.add_trace(go.Scatter(
    x=df_hist["stunde"],
    y=df_hist["preis"],
    mode="lines",
    name="Preisverlauf",
    line=dict(color="#C8CDD5", width=1.5, shape="hv"),
))

# 24h-Mittel — Corporate Blau
fig.add_trace(go.Scatter(
    x=df_24h["stunde"],
    y=df_24h["preis"],
    mode="lines",
    name="24h-Mittel",
    line=dict(color="#2C5F8A", width=2.5, shape="hv"),
))

# Prognose — gedämpftes Orange
fig.add_trace(go.Scatter(
    x=[jetzt_ts, prognose_ende],
    y=[prognose_preis, prognose_preis],
    mode="lines",
    name="Prognose 24h",
    line=dict(color="#D4820A", width=2.5, shape="hv"),
))

# Übergangspunkt
fig.add_trace(go.Scatter(
    x=[jetzt_ts],
    y=[letzter_preis],
    mode="markers",
    showlegend=False,
    marker=dict(color="#C0392B", size=8, symbol="circle"),
))

# Ø 24h Referenzlinie
fig.add_hline(
    y=mean_24h,
    line_dash="dot",
    line_color="#8892A0",
    opacity=0.6,
    annotation_text=f"Ø 24h: {mean_24h:.3f} €",
    annotation_position="bottom right",
    annotation_font_size=11,
    annotation_font_color="#8892A0",
)

# Mitternachts-Separatoren
mitternacht_linien = []
tag = cutoff_7d.normalize()
while tag <= jetzt_ts:
    mitternacht_linien.append(dict(
        type="line",
        x0=tag, x1=tag,
        y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#DDE1E8", width=1, dash="dot"),
    ))
    tag += pd.Timedelta(days=1)

fig.update_layout(
    shapes=mitternacht_linien,
    xaxis=dict(
        dtick=24 * 3600 * 1000,
        tick0="2020-01-01 12:00:00",
        tickformat="%d.%m.",
        tickangle=0,
        tickfont=dict(size=11, color="#8892A0"),
        gridcolor="#EEF0F3",
        showgrid=True,
    ),
    yaxis=dict(
        title="Preis (€)",
        tickfont=dict(size=11, color="#8892A0"),
        gridcolor="#EEF0F3",
        showgrid=True,
        title_font=dict(size=11, color="#8892A0"),
    ),
    legend=dict(
        orientation="h",
        font=dict(size=11, color="#6B7A8D"),
        bgcolor="rgba(0,0,0,0)",
    ),
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    margin=dict(l=0, r=0, t=10, b=0),
    height=320,
)

st.plotly_chart(fig, use_container_width=True)

# =========================================
# Footer
# =========================================
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(f"""
<div class='footer-text'>
    Preisinformationen bereitgestellt von <a href='https://tankerkoenig.de' target='_blank'>Tankerkönig</a>
    unter der <a href='https://creativecommons.org/licenses/by/4.0/' target='_blank'>Creative Commons Lizenz (CC BY 4.0)</a> ·
    Datenquelle: MTS-K (Markttransparenzstelle für Kraftstoffe) ·
    Modell: XGBoost · Prognose wird stündlich aktualisiert
</div>
""", unsafe_allow_html=True)