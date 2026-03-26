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
# CSS
# =========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Roboto', sans-serif;
    background-color: #F0F2F5 !important;
    color: #212529;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── TOPBAR ── */
.topbar {
    background: #1976D2;
    padding: 0 2rem;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    position: sticky;
    top: 0;
    z-index: 100;
}
.topbar-title {
    font-size: 1.15rem;
    font-weight: 500;
    color: #FFFFFF;
    letter-spacing: 0.01em;
}
.topbar-sub {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.7);
    margin-left: 1rem;
}
.topbar-time {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.85rem;
    color: rgba(255,255,255,0.85);
    background: rgba(0,0,0,0.15);
    padding: 4px 12px;
    border-radius: 4px;
}

/* ── MAIN CONTENT ── */
.main-content {
    padding: 1.5rem 2rem 3rem 2rem;
    max-width: 1200px;
    margin: 0 auto;
}

/* ── CARDS ── */
.card {
    background: #FFFFFF;
    border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
    padding: 1.25rem 1.5rem;
    height: 100%;
}
.card-title {
    font-size: 0.7rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9E9E9E;
    margin-bottom: 0.5rem;
}
.card-value {
    font-family: 'Roboto', sans-serif;
    font-size: 2.4rem;
    font-weight: 300;
    color: #212529;
    line-height: 1.1;
    letter-spacing: -0.01em;
}
.card-value sup {
    font-size: 0.45em;
    vertical-align: super;
    font-weight: 400;
    color: #757575;
}
.card-delta {
    font-size: 0.82rem;
    font-weight: 500;
    margin-top: 0.35rem;
    display: flex;
    align-items: center;
    gap: 3px;
}
.delta-green { color: #388E3C; }
.delta-red   { color: #D32F2F; }
.delta-blue  { color: #1565C0; }

/* Tendenz */
.tendenz-val {
    font-size: 3rem;
    font-weight: 300;
    line-height: 1;
}
.tendenz-down { color: #388E3C; }
.tendenz-up   { color: #D32F2F; }

/* ── EMPFEHLUNG ── */
.empfehlung-card {
    background: #FFFFFF;
    border-radius: 6px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
    padding: 1.25rem 1.5rem 1rem 1.5rem;
    border-left: 4px solid #1976D2;
    margin-bottom: 1.25rem;
}
.empfehlung-card.heute  { border-left-color: #388E3C; }
.empfehlung-card.morgen { border-left-color: #F57C00; }
.empfehlung-card.warten { border-left-color: #D32F2F; }

.empfehlung-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 3px;
    margin-bottom: 0.6rem;
}
.badge-heute  { background: #E8F5E9; color: #2E7D32; }
.badge-morgen { background: #FFF3E0; color: #E65100; }
.badge-warten { background: #FFEBEE; color: #C62828; }

.empfehlung-text {
    font-size: 0.95rem;
    color: #424242;
    line-height: 1.7;
}
.empfehlung-text strong {
    color: #212121;
    font-weight: 500;
}
.ki-footer {
    font-size: 0.68rem;
    color: #BDBDBD;
    margin-top: 0.75rem;
    padding-top: 0.6rem;
    border-top: 1px solid #F5F5F5;
}
.ki-footer a { color: #BDBDBD; }

/* ── SECTION TITLE ── */
.section-title {
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #9E9E9E;
    margin: 1.5rem 0 0.6rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #E0E0E0;
}

/* ── FOOTER ── */
.page-footer {
    margin-top: 2.5rem;
    padding-top: 1rem;
    border-top: 1px solid #E0E0E0;
    font-size: 0.68rem;
    color: #BDBDBD;
    line-height: 1.8;
}
.page-footer a { color: #BDBDBD; }

/* ── RESPONSIVE ── */
@media (max-width: 768px) {
    .topbar { padding: 0 1rem; }
    .main-content { padding: 1rem 1rem 2rem 1rem; }
    .card-value { font-size: 1.8rem; }
}
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

def bold(text):
    return text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

# =========================================
# TOPBAR
# =========================================
st.markdown(f"""
<div class="topbar">
    <div style="display:flex; align-items:baseline; gap:0.5rem;">
        <span class="topbar-title">Dieselpreisprognose</span>
        <span class="topbar-sub">ARAL · Dürener Str. 407 · Köln</span>
    </div>
    <span class="topbar-time">Live · {uhrzeit} Uhr</span>
</div>
""", unsafe_allow_html=True)

# =========================================
# MAIN CONTENT
# =========================================
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# ── Metriken ──
delta_val   = letzter_preis - mean_24h
delta_class = "delta-green" if delta_val < 0 else "delta-red"
delta_arrow = "↓" if delta_val < 0 else "↑"

tendenz_pfeil = "↓" if prognose["richtung_24h"] == "fällt" else "↑"
tendenz_class = "tendenz-down" if prognose["richtung_24h"] == "fällt" else "tendenz-up"

eval_row = f'<div class="card-delta delta-blue">Eval: {eval_text}</div>' if eval_text else ""

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown(f"""
    <div class="card">
        <div class="card-title">Ø letzte 24 Stunden</div>
        <div class="card-value">{preis_fmt(mean_24h)} €</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="card">
        <div class="card-title">Aktueller Preis · {uhrzeit} Uhr</div>
        <div class="card-value">{preis_fmt(letzter_preis)} €</div>
        <div class="card-delta {delta_class}">{delta_arrow} {abs(delta_val):.2f} € vs. Ø 24h</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="card">
        <div class="card-title">Tendenz nächste 24h</div>
        <div class="tendenz-val {tendenz_class}">{tendenz_pfeil}</div>
        {eval_row}
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

# ── Empfehlung ──
if "heute" in prognose["empfehlung"]:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", "Jetzt tanken"
elif "morgen" in prognose["empfehlung"]:
    card_cls, badge_cls, badge_txt = "morgen", "badge-morgen", "Morgen tanken"
else:
    card_cls, badge_cls, badge_txt = "warten", "badge-warten", "Abwarten"

st.markdown(f"""
<div class="empfehlung-card {card_cls}">
    <div class="empfehlung-badge {badge_cls}">{badge_txt}</div>
    <div class="empfehlung-text">{bold(ki_text)}</div>
    <div class="ki-footer">
        KI-generierter Text &middot;
        <a href="https://www.anthropic.com" target="_blank">Claude API · Anthropic</a> &middot;
        Modell: XGBoost &middot; Acc: {prognose['modell_accuracy']:.1f}% &middot;
        Keine Garantie
    </div>
</div>
""", unsafe_allow_html=True)

# ── Chart ──
st.markdown('<div class="section-title">Preisverlauf — 7 Tage + Prognose 24h</div>', unsafe_allow_html=True)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_hist["stunde"],
    y=df_hist["preis"],
    mode="lines",
    name="Preisverlauf",
    line=dict(color="#E0E0E0", width=1.5, shape="hv"),
))

fig.add_trace(go.Scatter(
    x=df_24h["stunde"],
    y=df_24h["preis"],
    mode="lines",
    name="24h-Mittel",
    line=dict(color="#1976D2", width=2.5, shape="hv"),
))

fig.add_trace(go.Scatter(
    x=[jetzt_ts, prognose_ende],
    y=[prognose_preis, prognose_preis],
    mode="lines",
    name="Prognose 24h",
    line=dict(color="#F57C00", width=2.5, shape="hv"),
))

fig.add_trace(go.Scatter(
    x=[jetzt_ts],
    y=[letzter_preis],
    mode="markers",
    showlegend=False,
    marker=dict(
        color="#FFFFFF",
        size=9,
        symbol="circle",
        line=dict(color="#1976D2", width=2.5)
    ),
))

fig.add_hline(
    y=mean_24h,
    line_dash="dot",
    line_color="#BDBDBD",
    annotation_text=f"Ø {mean_24h:.3f} €",
    annotation_position="bottom right",
    annotation_font=dict(size=11, color="#9E9E9E"),
)

mitternacht_linien = []
tag = cutoff_7d.normalize()
while tag <= jetzt_ts:
    mitternacht_linien.append(dict(
        type="line",
        x0=tag, x1=tag, y0=0, y1=1,
        xref="x", yref="paper",
        line=dict(color="#F5F5F5", width=1),
    ))
    tag += pd.Timedelta(days=1)

fig.update_layout(
    shapes=mitternacht_linien,
    plot_bgcolor="#FFFFFF",
    paper_bgcolor="#FFFFFF",
    font=dict(family="Roboto", size=12, color="#757575"),
    xaxis=dict(
        dtick=24 * 3600 * 1000,
        tick0="2020-01-01 12:00:00",
        tickformat="%d.%m.",
        tickangle=0,
        tickfont=dict(size=11, color="#9E9E9E"),
        gridcolor="#F5F5F5",
        showline=True,
        linecolor="#E0E0E0",
        zeroline=False,
    ),
    yaxis=dict(
        tickfont=dict(size=11, color="#9E9E9E"),
        gridcolor="#F5F5F5",
        showline=False,
        zeroline=False,
        ticksuffix=" €",
        title=None,
    ),
    legend=dict(
        orientation="h",
        y=-0.15,
        font=dict(size=11, color="#757575"),
        bgcolor="rgba(0,0,0,0)",
    ),
    margin=dict(l=10, r=20, t=15, b=10),
    height=340,
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#FFFFFF",
        bordercolor="#E0E0E0",
        font=dict(color="#212529", size=12),
    ),
)

st.plotly_chart(fig, use_container_width=True)

# ── Footer ──
st.markdown(f"""
<div class="page-footer">
    Preisinformationen von
    <a href="https://tankerkoenig.de" target="_blank">Tankerkönig</a>
    unter <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a> &middot;
    Datenquelle: MTS-K (Markttransparenzstelle für Kraftstoffe) &middot;
    Prognose stündlich via GitHub Actions &middot;
    DSI Capstone 2026
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)