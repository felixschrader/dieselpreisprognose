# dashboard.py
# Streamlit Dashboard — Spritpreisprognose ARAL Dürener Str. 407
# Tabs: Preisverlauf | Algo-KPIs | Modell-Performance

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from datetime import datetime
import pytz

st.set_page_config(
    page_title="Dieselpreis · Köln",
    page_icon="⛽",
    layout="centered"
)

STATION_UUID  = "e1aefc4e-3ca1-4018-8d91-455b69d35d41"
BASE_URL      = "https://raw.githubusercontent.com/felixschrader/spritpreisprognose/main"
JSON_URL      = f"{BASE_URL}/data/ml/prognose_aktuell.json"
PARQUET_URL   = f"{BASE_URL}/data/tankstellen_preise.parquet"
LOG_URL       = f"{BASE_URL}/data/ml/preis_live_log.csv"
PROGNOSE_LOG  = f"{BASE_URL}/data/ml/prognose_log.csv"
BERLIN        = pytz.timezone("Europe/Berlin")

# =========================================
# CSS
# =========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"], .stApp {
    font-family: 'Roboto', sans-serif;
    background-color: #F0F2F5 !important;
    color: #212529;
    font-size: 16px;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

.block-container {
    padding: 0 0 3rem 0 !important;
    max-width: 900px !important;
}

.topbar {
    background: #1565C0;
    padding: 0 2rem;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    margin-bottom: 1.5rem;
}
.topbar-left { display: flex; flex-direction: column; gap: 2px; }
.topbar-title { font-size: 1.6rem; font-weight: 500; color: #FFFFFF; line-height: 1.2; }
.topbar-sub   { font-size: 0.9rem; color: rgba(255,255,255,0.85); }
.topbar-time  {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.9rem; color: #FFFFFF;
    background: rgba(0,0,0,0.18);
    padding: 6px 14px; border-radius: 4px;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.25rem;
}
.card {
    background: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06);
    padding: 1.25rem 1.5rem;
}
.card-title {
    font-size: 0.75rem; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: #616161; margin-bottom: 0.5rem;
}
.card-value {
    font-size: clamp(2rem, 3vw, 2.6rem);
    font-weight: 300; color: #1A1A1A;
    line-height: 1.1; letter-spacing: -0.01em;
}
.card-value sup { font-size: 0.42em; vertical-align: super; font-weight: 400; color: #757575; }
.card-delta { font-size: 0.9rem; font-weight: 500; margin-top: 0.5rem; }
.delta-green { color: #2E7D32; }
.delta-red   { color: #C62828; }
.delta-blue  { color: #1565C0; }
.tendenz-val { font-size: clamp(2.4rem, 4vw, 3.2rem); font-weight: 300; line-height: 1; }
.tendenz-down { color: #2E7D32; }
.tendenz-up   { color: #C62828; }

.empfehlung-card {
    background: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 2px 8px rgba(0,0,0,0.06);
    padding: 1.4rem 1.5rem 1rem 1.5rem;
    border-left: 5px solid #1565C0;
    margin-bottom: 1.5rem;
}
.empfehlung-card.heute  { border-left-color: #2E7D32; }
.empfehlung-card.morgen { border-left-color: #E65100; }
.empfehlung-card.warten { border-left-color: #C62828; }
.empfehlung-badge {
    display: inline-block;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 4px; margin-bottom: 0.7rem;
}
.badge-heute  { background: #E8F5E9; color: #1B5E20; }
.badge-morgen { background: #FFF3E0; color: #BF360C; }
.badge-warten { background: #FFEBEE; color: #B71C1C; }
.empfehlung-text { font-size: 1rem; color: #212121; line-height: 1.8; }
.empfehlung-text strong { color: #1A1A1A; font-weight: 500; }
.ki-footer {
    font-size: 0.78rem; color: #9E9E9E;
    margin-top: 0.9rem; padding-top: 0.7rem;
    border-top: 1px solid #F5F5F5;
}
.ki-footer a { color: #757575; text-decoration: none; }

.section-label {
    font-size: 0.82rem; font-weight: 500;
    letter-spacing: 0.07em; text-transform: uppercase;
    color: #9E9E9E;
    margin: 1.5rem 0 0.6rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #E0E0E0;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.25rem;
}
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E8EAED;
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}
.kpi-val {
    font-family: 'Roboto Mono', monospace;
    font-size: 1.4rem; font-weight: 400; color: #1A1A1A;
}
.kpi-lbl {
    font-size: 0.68rem; font-weight: 500;
    letter-spacing: 0.08em; text-transform: uppercase;
    color: #9E9E9E; margin-top: 4px;
}

.page-footer {
    margin-top: 2rem; padding-top: 1rem;
    border-top: 1px solid #E0E0E0;
    font-size: 0.8rem; color: #9E9E9E; line-height: 2;
}
.page-footer a { color: #757575; text-decoration: none; }

@media (max-width: 640px) {
    .metric-grid { grid-template-columns: 1fr; }
    .kpi-grid    { grid-template-columns: repeat(2, 1fr); }
    .topbar      { padding: 0.75rem 1rem; height: auto; flex-wrap: wrap; gap: 0.5rem; }
    .topbar-sub  { display: none; }
}
</style>
""", unsafe_allow_html=True)

# =========================================
# Daten laden
# =========================================
@st.cache_data(ttl=300)
def lade_prognose():
    return requests.get(JSON_URL, timeout=10).json()

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
        return pd.DataFrame(columns=["timestamp", "preis", "richtung_6h", "richtung_12h"])

@st.cache_data(ttl=60)
def lade_aktueller_preis():
    try:
        key = st.secrets["TANKERKOENIG_KEY"]
        url = f"https://creativecommons.tankerkoenig.de/json/prices.php?ids={STATION_UUID}&apikey={key}"
        r   = requests.get(url, timeout=5)
        return float(r.json()["prices"][STATION_UUID]["diesel"])
    except:
        return None

@st.cache_data(ttl=3600)
def lade_prognose_log():
    try:
        df = pd.read_csv(PROGNOSE_LOG, parse_dates=["datum"])
        return df.sort_values("datum").reset_index(drop=True)
    except:
        return pd.DataFrame(columns=["datum", "predicted_delta", "actual_delta", "richtung_korrekt"])

@st.cache_data(ttl=3600)
def generiere_empfehlung(preis, mean_24h, richtung_6h, richtung_12h, dip_peak, empfehlung):
    prompt = f"""Du bist ein hilfreicher Tankstellen-Assistent für normale Autofahrer. Schreibe 2-3 Sätze auf Deutsch.

Fakten:
- Aktueller Dieselpreis: {preis:.3f} € ({preis - mean_24h:+.3f} € vs. 24h-Schnitt)
- Aktuelle Lage: {dip_peak} (Dip = günstiger als Nachbarn, Peak = teurer)
- Preistrend in 6 Stunden: {richtung_6h}
- Preistrend in 12 Stunden: {richtung_12h}
- Empfehlung: {empfehlung}

Regeln:
- Die Empfehlung "{empfehlung}" ist KORREKT — begründe sie überzeugend, stelle sie NICHT in Frage
- Erster Satz fett mit **: klare Handlungsempfehlung die mit "{empfehlung}" übereinstimmt
- Keine konkreten Eurobeträge für erwartete Preisänderungen nennen
- Kein Fachjargon, vorsichtig aber konsistent formulieren"""

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
df_prog_log = lade_prognose_log()

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

# --- Prognose-Linie (Bug fix: fester Drift statt broken Tweak) ---
prognose_stufen   = prognose.get("prognose_stufen", [])
df_prognose_linie = pd.DataFrame()

if prognose_stufen:
    DRIFT_PRO_STUNDE = 0.003  # 0.3 Cent pro Stunde — sichtbar, realistisch
    preis_sim = letzter_preis
    punkte    = [{"stunde": jetzt_ts, "preis": letzter_preis}]
    for s in prognose_stufen:
        preis_sim += DRIFT_PRO_STUNDE * (1 if s["richtung"] == "steigt" else -1)
        ts = jetzt_ts + pd.Timedelta(hours=s["stunde_offset"])
        punkte.append({"stunde": ts, "preis": round(preis_sim, 4)})
    df_prognose_linie = pd.DataFrame(punkte)

# Hilfswerte
cutoff_7d = jetzt_ts - pd.Timedelta(days=7)
df_plot   = df_ext[df_ext["stunde"] >= cutoff_7d].copy()

df_hist = pd.concat([
    df_plot[["stunde", "preis"]],
    df_live[df_live["stunde"] >= cutoff_7d][["stunde", "preis"]] if not df_live.empty else pd.DataFrame(columns=["stunde", "preis"]),
    pd.DataFrame([{"stunde": jetzt_ts, "preis": letzter_preis}])
]).sort_values("stunde").drop_duplicates("stunde", keep="last").reset_index(drop=True)

mean_24h     = float(df_hist[df_hist["stunde"] >= (jetzt_ts - pd.Timedelta(hours=24))]["preis"].mean())
richtung_6h  = prognose.get("richtung_6h", "unbekannt")
richtung_12h = prognose.get("richtung_12h", "unbekannt")
dip_peak     = prognose.get("dip_oder_peak", "")

try:
    ki_text = generiere_empfehlung(
        letzter_preis, mean_24h,
        richtung_6h, richtung_12h,
        dip_peak, prognose["empfehlung"]
    )
except:
    ki_text = f"**{prognose['empfehlung'].capitalize()}.** {prognose['begruendung']}"

def preis_fmt(p):
    s = f"{p:.3f}"
    return f"{s[:-1]}<sup>{s[-1]}</sup>"

def bold(text):
    return text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)

# =========================================
# TOPBAR
# =========================================
st.markdown(f"""
<div class="topbar" role="banner">
    <div class="topbar-left">
        <span class="topbar-title">Dieselpreisprognose</span>
        <span class="topbar-sub">ARAL &middot; Dürener Str. 407 &middot; Köln</span>
    </div>
    <span class="topbar-time">Live &middot; {uhrzeit} Uhr</span>
</div>
""", unsafe_allow_html=True)

# =========================================
# METRIKEN
# =========================================
delta_val     = letzter_preis - mean_24h
delta_class   = "delta-green" if delta_val < 0 else "delta-red"
delta_arrow   = "↓" if delta_val < 0 else "↑"
delta_label   = "günstiger" if delta_val < 0 else "teurer"
tendenz_pfeil = "↓" if richtung_6h == "fällt" else "↑"
tendenz_class = "tendenz-down" if richtung_6h == "fällt" else "tendenz-up"

st.markdown(f"""
<div class="metric-grid">
    <div class="card">
        <div class="card-title">Ø letzte 24 Stunden</div>
        <div class="card-value">{preis_fmt(mean_24h)} &euro;</div>
    </div>
    <div class="card">
        <div class="card-title">Aktueller Preis &middot; {uhrzeit} Uhr</div>
        <div class="card-value">{preis_fmt(letzter_preis)} &euro;</div>
        <div class="card-delta {delta_class}">{delta_arrow} {abs(delta_val):.2f} &euro; vs. &Oslash; 24h</div>
    </div>
    <div class="card">
        <div class="card-title">Tendenz nächste 6h</div>
        <div class="tendenz-val {tendenz_class}">{tendenz_pfeil}</div>
        <div class="card-delta delta-blue">12h: {richtung_12h}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# EMPFEHLUNG
# =========================================
if "heute" in prognose["empfehlung"]:
    card_cls, badge_cls, badge_txt = "heute", "badge-heute", "Jetzt tanken"
elif "morgen" in prognose["empfehlung"] or "später" in prognose["empfehlung"]:
    card_cls, badge_cls, badge_txt = "morgen", "badge-morgen", "Später tanken"
else:
    card_cls, badge_cls, badge_txt = "warten", "badge-warten", "Abwarten"

st.markdown(f"""
<div class="empfehlung-card {card_cls}">
    <div class="empfehlung-badge {badge_cls}">{badge_txt}</div>
    <div class="empfehlung-text">{bold(ki_text)}</div>
    <div class="ki-footer">
        KI-generierter Text &middot;
        <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude API &middot; Anthropic</a>
        &middot; Modell: Random Forest MultiOutput &middot; Acc: {prognose['modell_accuracy']:.1f}% &middot; Keine Garantie
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================
# TABS
# =========================================
tab1, tab2, tab3 = st.tabs(["📈 Preisverlauf", "🔍 Algo-KPIs", "📊 Modell-Performance"])

# ─── TAB 1: Preisverlauf ─────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-label">Preisverlauf — 7 Tage + Prognose 24h</div>', unsafe_allow_html=True)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_hist["stunde"], y=df_hist["preis"],
        mode="lines", name="Preisverlauf",
        line=dict(color="#BDBDBD", width=1.5, shape="hv"),
    ))

    # 24h-Mittel
    bin_grenzen = [jetzt_ts - pd.Timedelta(hours=24 * i) for i in range(8, -1, -1)]
    df_24h_rows = []
    for i in range(len(bin_grenzen) - 1):
        mask = (df_hist["stunde"] >= bin_grenzen[i]) & (df_hist["stunde"] < bin_grenzen[i+1])
        if mask.sum() > 0:
            df_24h_rows.append({"stunde": bin_grenzen[i], "preis": df_hist.loc[mask, "preis"].mean()})
    if df_24h_rows:
        df_24h = pd.DataFrame(df_24h_rows + [{"stunde": jetzt_ts, "preis": letzter_preis}])
        fig.add_trace(go.Scatter(
            x=df_24h["stunde"], y=df_24h["preis"],
            mode="lines", name="24h-Mittel",
            line=dict(color="#1565C0", width=2.5, shape="hv"),
        ))

    # Prognose-Linie (fixed)
    if not df_prognose_linie.empty:
        fig.add_trace(go.Scatter(
            x=df_prognose_linie["stunde"], y=df_prognose_linie["preis"],
            mode="lines", name="Prognose 24h",
            line=dict(color="#E65100", width=2, shape="hv", dash="dot"),
        ))

    fig.add_trace(go.Scatter(
        x=[jetzt_ts], y=[letzter_preis],
        mode="markers", showlegend=False,
        marker=dict(color="#FFFFFF", size=10, symbol="circle",
                    line=dict(color="#1565C0", width=2.5)),
    ))

    fig.add_vline(x=jetzt_ts, line_width=1, line_dash="dash", line_color="#BDBDBD")

    mitternacht_linien = []
    tag = cutoff_7d.normalize()
    while tag <= jetzt_ts + pd.Timedelta(days=1):
        mitternacht_linien.append(dict(
            type="line", x0=tag, x1=tag, y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="#EEEEEE", width=1),
        ))
        tag += pd.Timedelta(days=1)

    fig.update_layout(
        shapes=mitternacht_linien,
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        font=dict(family="Roboto", size=13, color="#757575"),
        xaxis=dict(dtick=24*3600*1000, tick0="2020-01-01 12:00:00",
                   tickformat="%d.%m.", tickangle=0,
                   tickfont=dict(size=13, color="#9E9E9E"),
                   gridcolor="#F5F5F5", showline=True,
                   linecolor="#E0E0E0", zeroline=False),
        yaxis=dict(tickfont=dict(size=13, color="#9E9E9E"),
                   gridcolor="#F5F5F5", zeroline=False,
                   ticksuffix=" €", title=None),
        legend=dict(orientation="h", y=-0.15,
                    font=dict(size=13, color="#757575"),
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=20, t=15, b=10),
        height=360, hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#E0E0E0",
                        font=dict(color="#212529", size=13, family="Roboto")),
    )
    st.plotly_chart(fig, use_container_width=True)

# ─── TAB 2: Algo-KPIs ────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-label">Algorithmus-Analyse — letzte 90 Tage</div>', unsafe_allow_html=True)

    cutoff_90d = jetzt_ts - pd.Timedelta(days=90)
    df_90 = df_hist[df_hist["stunde"] >= cutoff_90d].copy()
    df_90 = df_90.sort_values("stunde")
    df_90["delta"] = df_90["preis"].diff()
    df_90["tag"]   = df_90["stunde"].dt.date
    df_90["stunde_h"] = df_90["stunde"].dt.hour

    erhoehungen = (df_90["delta"] > 0.001).sum()
    senkungen   = (df_90["delta"] < -0.001).sum()
    ratio       = erhoehungen / senkungen if senkungen > 0 else 0
    aend_tag    = df_90.groupby("tag")["delta"].count().mean()

    # IQR Kernstunden 13-20h
    kern_90 = df_90[df_90["stunde_h"].between(13, 20)]
    iqr_kern = (
        kern_90.groupby("tag")["preis"]
        .agg(lambda x: x.quantile(0.75) - x.quantile(0.25))
        .mean()
    )
    volatilitaet = df_90.groupby("tag")["preis"].std().mean()

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-val">{erhoehungen:,}</div>
            <div class="kpi-lbl">Erhöhungen</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{senkungen:,}</div>
            <div class="kpi-lbl">Senkungen</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{ratio:.2f}</div>
            <div class="kpi-lbl">Ratio E/S</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{aend_tag:.1f}</div>
            <div class="kpi-lbl">Ø Ändg/Tag</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{iqr_kern*100:.1f}<span style="font-size:0.75rem"> ct</span></div>
            <div class="kpi-lbl">IQR Kernzeit</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val">{volatilitaet*100:.1f}<span style="font-size:0.75rem"> ct</span></div>
            <div class="kpi-lbl">Ø Volatilität</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Erhöhungen nach Wochentag
    st.markdown('<div class="section-label">Erhöhungen vs. Senkungen nach Wochentag</div>', unsafe_allow_html=True)
    df_90["wochentag"] = pd.to_datetime(df_90["tag"]).dt.dayofweek
    wt_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    erh_wt = df_90[df_90["delta"] > 0.001].groupby("wochentag").size()
    sen_wt = df_90[df_90["delta"] < -0.001].groupby("wochentag").size()

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=[wt_labels[i] for i in erh_wt.index], y=erh_wt.values,
        name="Erhöhungen", marker_color="#C62828", opacity=0.8,
    ))
    fig2.add_trace(go.Bar(
        x=[wt_labels[i] for i in sen_wt.index], y=sen_wt.values,
        name="Senkungen", marker_color="#2E7D32", opacity=0.8,
    ))
    fig2.update_layout(
        barmode="group", plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#F5F5F5"),
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False),
        legend=dict(orientation="h", y=-0.25),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Erhöhungen nach Stunde
    st.markdown('<div class="section-label">Erhöhungen nach Tagesstunde — Rockets & Feathers</div>', unsafe_allow_html=True)
    erh_stunde = df_90[df_90["delta"] > 0.001].groupby("stunde_h").size()

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=erh_stunde.index, y=erh_stunde.values,
        marker_color="#1565C0", opacity=0.8,
    ))
    fig3.update_layout(
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        height=230, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#F5F5F5", dtick=1, title="Stunde"),
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False),
        showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

    # IQR als Linie
    st.markdown('<div class="section-label">IQR Kernzeit (13–20h) pro Tag — Intraday-Volatilität</div>', unsafe_allow_html=True)
    df_iqr = (
        kern_90.groupby("tag")["preis"]
        .agg(lambda x: x.quantile(0.75) - x.quantile(0.25))
        .reset_index()
    )
    df_iqr["tag"] = pd.to_datetime(df_iqr["tag"])

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=df_iqr["tag"], y=df_iqr["preis"] * 100,
        mode="lines", line=dict(color="#6A1B9A", width=1.5),
        fill="tozeroy", fillcolor="rgba(106,27,154,0.1)",
    ))
    fig4.add_hline(
        y=df_iqr["preis"].mean() * 100,
        line_dash="dash", line_color="#9E9E9E", line_width=1,
        annotation_text=f"Ø {df_iqr['preis'].mean()*100:.1f} ct",
    )
    fig4.update_layout(
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        height=220, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#F5F5F5"),
        yaxis=dict(gridcolor="#F5F5F5", zeroline=False, ticksuffix=" ct"),
        showlegend=False,
    )
    st.plotly_chart(fig4, use_container_width=True)

# ─── TAB 3: Modell-Performance ───────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-label">Retrograde Modell-Bewertung — letzte 30 Tage</div>', unsafe_allow_html=True)

    if df_prog_log.empty:
        st.info("Noch keine Prognose-Log-Daten verfügbar. Der Log wird täglich durch GitHub Actions befüllt.")
    else:
        df_log_30 = df_prog_log[
            df_prog_log["datum"] >= (jetzt_ts - pd.Timedelta(days=30))
        ].copy()

        if not df_log_30.empty and "richtung_korrekt" in df_log_30.columns:
            richtung_acc = df_log_30["richtung_korrekt"].mean() * 100
            mae_30       = df_log_30["actual_delta"].sub(df_log_30["predicted_delta"]).abs().mean() * 100
            n_tage       = len(df_log_30)

            st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-val">{richtung_acc:.1f}<span style="font-size:0.75rem">%</span></div>
                    <div class="kpi-lbl">Richtungs-Accuracy</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-val">{mae_30:.2f}<span style="font-size:0.75rem"> ct</span></div>
                    <div class="kpi-lbl">MAE (Cent)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-val">{n_tage}</div>
                    <div class="kpi-lbl">Tage bewertet</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-val">67.9<span style="font-size:0.75rem">%</span></div>
                    <div class="kpi-lbl">Accuracy Test-Set</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Predicted vs. Actual Scatter
            st.markdown('<div class="section-label">Predicted vs. Actual Delta (Cent)</div>', unsafe_allow_html=True)
            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=df_log_30["predicted_delta"] * 100,
                y=df_log_30["actual_delta"] * 100,
                mode="markers",
                marker=dict(
                    color=df_log_30["richtung_korrekt"].map({1: "#2E7D32", 0: "#C62828"}),
                    size=8, opacity=0.7,
                ),
                text=df_log_30["datum"].astype(str),
                hovertemplate="Datum: %{text}<br>Predicted: %{x:.2f} ct<br>Actual: %{y:.2f} ct",
                name="Prognose",
            ))
            # Diagonale (perfekte Prognose)
            lim = max(
                abs(df_log_30["predicted_delta"].max()),
                abs(df_log_30["actual_delta"].max())
            ) * 100 * 1.1
            fig5.add_trace(go.Scatter(
                x=[-lim, lim], y=[-lim, lim],
                mode="lines", line=dict(color="#9E9E9E", dash="dash", width=1),
                showlegend=False,
            ))
            fig5.update_layout(
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                height=320, margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title="Predicted (Cent)", gridcolor="#F5F5F5", zeroline=True, zerolinecolor="#E0E0E0"),
                yaxis=dict(title="Actual (Cent)", gridcolor="#F5F5F5", zeroline=True, zerolinecolor="#E0E0E0"),
                showlegend=False,
            )
            st.plotly_chart(fig5, use_container_width=True)
            st.caption("Grün = Richtung korrekt, Rot = Richtung falsch. Punkte auf der Diagonale = perfekte Prognose.")

            # Trefferquote nach Wochentag
            st.markdown('<div class="section-label">Trefferquote nach Wochentag</div>', unsafe_allow_html=True)
            df_log_30["wochentag"] = df_log_30["datum"].dt.dayofweek
            wt_acc = df_log_30.groupby("wochentag")["richtung_korrekt"].mean() * 100
            wt_labels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

            fig6 = go.Figure()
            fig6.add_trace(go.Bar(
                x=[wt_labels[i] for i in wt_acc.index],
                y=wt_acc.values,
                marker_color=["#2E7D32" if v >= 60 else "#C62828" for v in wt_acc.values],
                opacity=0.8,
            ))
            fig6.add_hline(y=50, line_dash="dash", line_color="#9E9E9E", line_width=1,
                           annotation_text="Münzwurf 50%")
            fig6.add_hline(y=67.9, line_dash="dot", line_color="#1565C0", line_width=1,
                           annotation_text="Test-Set Acc 67.9%")
            fig6.update_layout(
                plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
                height=250, margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(gridcolor="#F5F5F5"),
                yaxis=dict(gridcolor="#F5F5F5", zeroline=False,
                           ticksuffix="%", range=[0, 100]),
                showlegend=False,
            )
            st.plotly_chart(fig6, use_container_width=True)

        else:
            st.info("Prognose-Log vorhanden aber unvollständig — Spalten fehlen.")

# =========================================
# FOOTER
# =========================================
st.markdown(f"""
<div class="page-footer">
    Preisinformationen von
    <a href="https://tankerkoenig.de" target="_blank" rel="noopener">Tankerkönig</a>
    unter <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>
    &middot; Datenquelle: MTS-K (Markttransparenzstelle für Kraftstoffe)
    &middot; Prognose stündlich via GitHub Actions
    &middot; DSI Capstone 2026
</div>
""", unsafe_allow_html=True)
