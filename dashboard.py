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
    page_title="Dieselpreis · Köln",
    page_icon="⛽",
    layout="wide"
)

STATION_UUID = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
JSON_URL     = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/prognose_aktuell.json"
PARQUET_URL  = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/tankstellen_preise.parquet"
LOG_URL      = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main/data/ml/preis_live_log.csv"
BERLIN       = pytz.timezone("Europe/Berlin")

# =========================================
# Premium CSS
# =========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    background: #0A0E1A !important;
    color: #E8EDF5;
}

.block-container {
    padding: 2rem 2rem 4rem 2rem !important;
    max-width: 1200px !important;
}

/* Streamlit default elements ausblenden */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── HEADER ── */
.dash-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    padding: 2rem 0 2.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    margin-bottom: 2.5rem;
}
.dash-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(1.8rem, 4vw, 3rem);
    font-weight: 800;
    color: #FFFFFF;
    letter-spacing: -0.03em;
    line-height: 1;
}
.dash-title span {
    background: linear-gradient(135deg, #4F9CF9 0%, #A78BFA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.dash-subtitle {
    font-size: 0.82rem;
    color: #5A6478;
    margin-top: 0.4rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.dash-timestamp {
    text-align: right;
    font-size: 0.78rem;
    color: #5A6478;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.dash-timestamp strong {
    display: block;
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #A0AEC0;
    margin-top: 2px;
}

/* ── METRIC CARDS ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}
@media (max-width: 768px) {
    .metric-grid { grid-template-columns: 1fr; }
}
.metric-card {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 1.5rem 1.75rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, rgba(79,156,249,0.4), transparent);
}
.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(79,156,249,0.2);
}
.metric-label {
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #4A5568;
    margin-bottom: 0.75rem;
}
.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2rem, 3.5vw, 2.8rem);
    font-weight: 700;
    color: #F0F4FF;
    line-height: 1;
    letter-spacing: -0.02em;
}
.metric-value sup {
    font-size: 0.5em;
    vertical-align: super;
    font-weight: 600;
    opacity: 0.7;
}
.metric-delta {
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 0.5rem;
    display: flex;
    align-items: center;
    gap: 4px;
}
.delta-pos { color: #F87171; }
.delta-neg { color: #34D399; }
.delta-neutral { color: #60A5FA; }

/* Tendenz-Pfeil groß */
.tendenz-pfeil {
    font-size: clamp(2.5rem, 5vw, 3.5rem);
    font-weight: 700;
    line-height: 1;
    font-family: 'Syne', sans-serif;
}
.tendenz-down { color: #34D399; }
.tendenz-up   { color: #F87171; }

/* ── EMPFEHLUNG BOX ── */
.empfehlung-wrap {
    background: #121828;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.empfehlung-wrap::after {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 180px; height: 180px;
    border-radius: 50%;
    opacity: 0.04;
}
.empfehlung-heute::after  { background: #34D399; }
.empfehlung-morgen::after { background: #FBBF24; }
.empfehlung-warten::after { background: #F87171; }

.empfehlung-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    margin-bottom: 0.85rem;
}
.badge-heute  { background: rgba(52,211,153,0.12); color: #34D399; border: 1px solid rgba(52,211,153,0.2); }
.badge-morgen { background: rgba(251,191,36,0.12);  color: #FBBF24; border: 1px solid rgba(251,191,36,0.2); }
.badge-warten { background: rgba(248,113,113,0.12); color: #F87171; border: 1px solid rgba(248,113,113,0.2); }

.empfehlung-text {
    font-size: clamp(0.9rem, 1.5vw, 1.02rem);
    color: #CBD5E1;
    line-height: 1.75;
}
.empfehlung-text strong {
    color: #F0F4FF;
    font-weight: 600;
}
.ki-disclaimer {
    font-size: 0.68rem;
    color: #2D3748;
    margin-top: 1rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255,255,255,0.04);
}
.ki-disclaimer a { color: #4A5568; text-decoration: none; }

/* ── CHART SECTION ── */
.chart-header {
    font-family: 'Syne', sans-serif;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #4A5568;
    margin-bottom: 0.75rem;
}

/* ── FOOTER ── */
.dash-footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    font-size: 0.7rem;
    color: #2D3748;
    line-height: 1.8;
}
.dash-footer a { color: #3D4F6A; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

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
- Wenn Signal-Rausch unter 0.5: erwartete Änderung könnte durch Preisschwankungen aufgehoben werden
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

if not df_live_raw.empty and "timestamp" in df_live_raw.columns:
    df_live = df_live_raw[["timestamp", "preis"]].copy()
    df_live = df_live.rename(columns={"timestamp": "stunde"})
    df_live["stunde"] = pd.to_datetime(df_live["stunde"])
    df_live = df_live.sort_values("stunde").drop_duplicates("stunde").reset_index(drop=True)
else:
    df_live = pd.DataFrame(columns=["stunde", "preis"])

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

jetzt_ts      = pd.Timestamp(datetime.now(BERLIN)).tz_localize(None)
letzter_preis = preis_live if preis_live else float(prognose["preis_aktuell"])
uhrzeit       = jetzt_ts.strftime("%H:%M")

delta_erwartet = float(prognose["delta_erwartet"])
if prognose["richtung_24h"] == "fällt":
    delta_erwartet = -abs(delta_erwartet)
else:
    delta_erwartet = abs(delta_erwartet)

prognose_preis = letzter_preis + delta_erwartet
prognose_ende  = jetzt_ts + pd.Timedelta(hours=24)

cutoff_7d = jetzt_ts - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

df_hist = pd.concat([
    df_plot[["stunde", "preis"]],
    df_live[df_live["stunde"] >= cutoff_7d][["stunde", "preis"]] if not df_live.empty else pd.DataFrame(columns=["stunde", "preis"]),
    pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
]).sort_values("stunde").drop_duplicates("stunde", keep="last").reset_index(drop=True)

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

eval_text = None
if not df_live_raw.empty and "tendenz_24h" in df_live_raw.columns:
    df_live_raw["timestamp"] = pd.to_datetime(df_live_raw["timestamp"])
    ziel_ts  = jetzt_ts - pd.Timedelta(hours=24)
    toleranz = pd.Timedelta(minutes=30)
    df_t24   = df_live_raw[
        (df_live_raw["timestamp"] >= ziel_ts - toleranz) &
        (df_live_raw["timestamp"] <= ziel_ts + toleranz)
    ]
    if not df_t24.empty and not pd.isna(df_t24.iloc[-1].get("tendenz_24h", float("nan"))):
        eval_diff = letzter_preis - (float(df_t24.iloc[-1]["preis"]) + float(df_t24.iloc[-1]["tendenz_24h"]))
        eval_text = f"{eval_diff:+.3f} €"

signal_rausch = abs(delta_erwartet) / float(prognose["volatilitaet_7d"]) if float(prognose["volatilitaet_7d"]) > 0 else 0

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
    return f"{s[:-1]}<sup>{s[-1]}</sup>"

# =========================================
# HEADER
# =========================================
st.markdown(f"""
<div class="dash-header">
    <div>
        <div class="dash-title">Diesel<span>prognose</span></div>
        <div class="dash-subtitle">ARAL · Dürener Str. 407 · Köln</div>
    </div>
    <div class="dash-timestamp">
        Live-Daten
        <strong>{uhrzeit} Uhr</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# METRIKEN
# =========================================
delta_val   = letzter_preis - mean_24h
delta_class = "delta-neg" if delta_val < 0 else "delta-pos"
delta_sign  = "↓" if delta_val < 0 else "↑"

tendenz_pfeil = "↓" if prognose["richtung_24h"] == "fällt" else "↑"
tendenz_class = "tendenz-down" if prognose["richtung_24h"] == "fällt" else "tendenz-up"

eval_html = f"<div class='metric-delta delta-neutral'>Eval: {eval_text}</div>" if eval_text else ""

st.markdown(f"""
<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-label">Ø letzte 24 Stunden</div>
        <div class="metric-value">{preis_fmt(mean_24h)} €</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Aktueller Preis · {uhrzeit} Uhr</div>
        <div class="metric-value">{preis_fmt(letzter_preis)} €</div>
        <div class="metric-delta {delta_class}">{delta_sign} {abs(delta_val):.2f} € vs. Ø 24h</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">Tendenz nächste 24h</div>
        <div class="metric-value tendenz-pfeil {tendenz_class}">{tendenz_pfeil}</div>
        {eval_html}
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# KI-EMPFEHLUNG
# =========================================
if "heute" in prognose["empfehlung"]:
    box_class   = "empfehlung-heute"
    badge_class = "badge-heute"
    badge_text  = "Jetzt tanken"
elif "morgen" in prognose["empfehlung"]:
    box_class   = "empfehlung-morgen"
    badge_class = "badge-morgen"
    badge_text  = "Morgen tanken"
else:
    box_class   = "empfehlung-warten"
    badge_class = "badge-warten"
    badge_text  = "Abwarten"

ki_html = ki_text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

st.markdown(f"""
<div class="empfehlung-wrap {box_class}">
    <div class="empfehlung-badge {badge_class}">{badge_text}</div>
    <div class="empfehlung-text">{ki_html}</div>
    <div class="ki-disclaimer">
        KI-generierter Text · <a href="https://www.anthropic.com" target="_blank">Claude API · Anthropic</a> ·
        Modell: XGBoost · Acc: {prognose['modell_accuracy']:.1f}% · Keine Garantie
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# CHART
# =========================================
st.markdown("<div class='chart-header'>Preisverlauf — 7 Tage + Prognose 24h</div>", unsafe_allow_html=True)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_hist["stunde"],
    y=df_hist["preis"],
    mode="lines",
    name="Preisverlauf",
    line=dict(color="rgba(255,255,255,0.12)", width=1.5, shape="hv"),
))

fig.add_trace(go.Scatter(
    x=df_24h["stunde"],
    y=df_24h["preis"],
    mode="lines",
    name="24h-Mittel",
    line=dict(color="#4F9CF9", width=2.5, shape="hv"),
))

fig.add_trace(go.Scatter(
    x=[jetzt_ts, prognose_ende],
    y=[prognose_preis, prognose_preis],
    mode="lines",
    name="Prognose 24h",
    line=dict(color="#A78BFA", width=2.5, shape="hv"),
))

fig.add_trace(go.Scatter(
    x=[jetzt_ts],
    y=[letzter_preis],
    mode="markers",
    showlegend=False,
    marker=dict(color="#F0F4FF", size=8, symbol="circle",
                line=dict(color="#4F9CF9", width=2)),
))

fig.add_hline(
    y=mean_24h,
    line_dash="dot",
    line_color="rgba(79,156,249,0.25)",
    annotation_text=f"Ø {mean_24h:.3f} €",
    annotation_position="bottom right",
    annotation_font=dict(size=11, color="#4A5568"),
)

mitternacht_linien = []
tag = cutoff_7d.normalize()
while tag <= jetzt_ts:
    mitternacht_linien.append(dict(
        type="line",
        x0=tag, x1=tag, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="rgba(255,255,255,0.04)", width=1),
    ))
    tag += pd.Timedelta(days=1)

fig.update_layout(
    shapes=mitternacht_linien,
    plot_bgcolor="#0D1220",
    paper_bgcolor="#121828",
    font=dict(family="Inter", color="#4A5568"),
    xaxis=dict(
        dtick=24 * 3600 * 1000,
        tick0="2020-01-01 12:00:00",
        tickformat="%d.%m.",
        tickangle=0,
        tickfont=dict(size=11, color="#4A5568"),
        gridcolor="rgba(255,255,255,0.03)",
        showline=False,
        zeroline=False,
    ),
    yaxis=dict(
        tickfont=dict(size=11, color="#4A5568"),
        gridcolor="rgba(255,255,255,0.04)",
        showline=False,
        zeroline=False,
        title=None,
        ticksuffix=" €",
    ),
    legend=dict(
        orientation="h",
        y=-0.12,
        font=dict(size=11, color="#4A5568"),
        bgcolor="rgba(0,0,0,0)",
    ),
    margin=dict(l=10, r=10, t=20, b=10),
    height=340,
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#1A2234",
        bordercolor="rgba(79,156,249,0.3)",
        font=dict(color="#E8EDF5", size=12),
    ),
)

st.plotly_chart(fig, use_container_width=True)

# =========================================
# FOOTER
# =========================================
st.markdown(f"""
<div class="dash-footer">
    Preisinformationen von <a href="https://tankerkoenig.de" target="_blank">Tankerkönig</a>
    unter <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a> ·
    Datenquelle: MTS-K (Markttransparenzstelle für Kraftstoffe) ·
    Prognose stündlich aktualisiert via GitHub Actions ·
    Spritpreisprognose · DSI Capstone 2026
</div>
""", unsafe_allow_html=True)