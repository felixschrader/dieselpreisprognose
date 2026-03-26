# dashboard.py
# Streamlit Dashboard — Spritpreisprognose ARAL Dürener Str. 407
# Läuft auf Streamlit Cloud, liest prognose_aktuell.json aus dem Repo

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import requests
from datetime import datetime
import pytz

# =========================================
# Konfiguration
# =========================================
st.set_page_config(
    page_title="Spritpreis Köln",
    page_icon="⛽",
    layout="centered"
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
JSON_URL     = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/prognose_aktuell.json"
PARQUET_URL  = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/tankstellen_preise.parquet"
BERLIN       = pytz.timezone("Europe/Berlin")

# =========================================
# Daten laden
# =========================================
@st.cache_data(ttl=300)  # 5 Minuten Cache
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
    # Letzte 7 Tage
    cutoff = df["date"].max() - pd.Timedelta(days=7)
    df = df[df["date"] >= cutoff]
    # Stundenbins
    df["stunde"] = df["date"].dt.floor("h")
    df = df.groupby("stunde").agg(preis=("diesel", "mean")).reset_index()
    return df

prognose = lade_prognose()
df_plot  = lade_preisverlauf()

# =========================================
# Header
# =========================================
st.title("⛽ Diesel-Preisprognose")
st.caption(f"ARAL Dürener Str. 407, Köln · Stand: {prognose['timestamp']} Uhr")

st.divider()

# =========================================
# Empfehlung — Hauptkarte
# =========================================
empfehlung = prognose["empfehlung"]
begruendung = prognose["begruendung"]

if "heute" in empfehlung:
    farbe = "green"
    emoji = "🟢"
elif "morgen" in empfehlung:
    farbe = "orange"
    emoji = "🟡"
else:
    farbe = "red"
    emoji = "🔴"

st.markdown(f"""
<div style='background-color: {"#d4edda" if farbe=="green" else "#fff3cd" if farbe=="orange" else "#f8d7da"};
            padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
    <h1 style='margin:0; font-size: 2.5em;'>{emoji}</h1>
    <h2 style='margin:5px 0;'>{empfehlung.capitalize()}</h2>
    <p style='margin:0; color: #555;'>{begruendung}</p>
</div>
""", unsafe_allow_html=True)

# =========================================
# Metriken — 3 Spalten
# =========================================
col1, col2, col3 = st.columns(3)

with col1:
    dip_peak = prognose["dip_oder_peak"]
    abweichung = prognose["abweichung_t0_24h"]
    delta_str = f"{abweichung:+.3f} €"
    st.metric(
        label="Aktueller Preis",
        value=f"{prognose['preis_aktuell']:.3f} €",
        delta=f"{dip_peak} ({delta_str})",
        delta_color="inverse"
    )

with col2:
    richtung = prognose["richtung_24h"]
    richtung_emoji = "📈" if richtung == "steigt" else "📉"
    st.metric(
        label="Prognose 24h",
        value=f"{richtung_emoji} {richtung}",
        delta=f"Konfidenz: {prognose['konfidenz']:.1f}%",
        delta_color="off"
    )

with col3:
    st.metric(
        label="Ø letzte 24h",
        value=f"{prognose['mean_24h_rueck']:.3f} €",
        delta=f"Volatilität: ±{prognose['volatilitaet_7d']:.3f} €",
        delta_color="off"
    )

st.divider()

# =========================================
# Preisverlauf letzte 7 Tage
# =========================================
st.subheader("Preisverlauf — letzte 7 Tage")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_plot["stunde"],
    y=df_plot["preis"],
    mode="lines",
    name="Dieselpreis",
    line=dict(color="#1f77b4", width=1.5),
))

# Aktueller Preis als Punkt
fig.add_trace(go.Scatter(
    x=[pd.Timestamp(prognose["timestamp"])],
    y=[prognose["preis_aktuell"]],
    mode="markers",
    name="Aktuell",
    marker=dict(color="red", size=10, symbol="circle"),
))

# 24h-Mittel als Linie
fig.add_hline(
    y=prognose["mean_24h_rueck"],
    line_dash="dash",
    line_color="gray",
    annotation_text=f"Ø 24h: {prognose['mean_24h_rueck']:.3f} €",
    annotation_position="bottom right"
)

fig.update_layout(
    xaxis_title="Datum",
    yaxis_title="Preis (€)",
    legend=dict(orientation="h"),
    margin=dict(l=0, r=0, t=10, b=0),
    height=300,
)

st.plotly_chart(fig, use_container_width=True)

# =========================================
# Footer
# =========================================
st.divider()
st.caption(
    f"Modell: XGBoost · Trainingsgenauigkeit: {prognose['modell_accuracy']:.1f}% · "
    f"Prognose wird stündlich aktualisiert"
)