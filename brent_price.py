import yfinance as yf
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import pytz

# Quelle: Yahoo Finance — Brent Crude Oil Last Day Financial Futures (BZ=F)
# Börse: NY Mercantile (NYMEX), cash-settled, USD/Barrel
# Tagesdaten: historisch seit 2014-01-01, unbegrenzt
# Intraday:   stündlich, maximal letzte 60 Tage verfügbar

CSV_DAILY     = "data/brent_futures_daily.csv"
CSV_INTRADAY  = "data/brent_futures_intraday_1h.csv"
PLOT_DAILY    = "plots/brent_futures_daily.html"
PLOT_INTRADAY = "plots/brent_futures_intraday_1h.html"
HISTORY_START = "2014-01-01"


# ── 1) Tagesdaten ────────────────────────────────────────────────────────────

def fetch_daily(start: str) -> pd.DataFrame:
    """
    Tägliche Schlusskurse Brent Crude Oil Futures (BZ=F).
    Quelle: Yahoo Finance via yfinance
    Spalte: brent_futures_usd (USD/Barrel, Close)
    """
    ticker = yf.Ticker("BZ=F")
    raw = ticker.history(start=start, interval="1d", auto_adjust=True)

    if raw.empty:
        raise ValueError("yfinance hat keine Tagesdaten zurückgegeben.")

    df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "period"
    df = df.rename(columns={"Close": "brent_futures_usd"})
    df = df.dropna()
    return df


def update_daily() -> dict:
    """Tagesdaten: ab letztem Datenpunkt in CSV nachfüllen (append)."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("plots", exist_ok=True)

    if os.path.exists(CSV_DAILY):
        df_existing = pd.read_csv(CSV_DAILY, index_col=0, parse_dates=True)
        df_existing.index.name = "period"
        last_ts = df_existing.index[-1]
        fetch_start = last_ts.strftime("%Y-%m-%d")
    else:
        df_existing = None
        fetch_start = HISTORY_START

    try:
        df_new = fetch_daily(start=fetch_start)
    except Exception as e:
        print(f"❌ yfinance täglich fehlgeschlagen: {e}")
        return {}

    if df_existing is not None:
        df_append = df_new[df_new.index > df_existing.index[-1]]
        if df_append.empty:
            print("ℹ️  Tagesdaten: keine neuen Daten.")
            df = df_existing
        else:
            df = pd.concat([df_existing, df_append]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
            print(f"✅ yfinance täglich (BZ=F): {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        df = df_new
        print(f"✅ yfinance täglich (BZ=F): {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    df.to_csv(CSV_DAILY)
    print(f"📄 CSV gespeichert: {CSV_DAILY}")

    fig = px.line(df, x=df.index, y="brent_futures_usd",
                  title="Brent Crude Oil Futures (BZ=F) — täglich | Quelle: Yahoo Finance",
                  labels={"brent_futures_usd": "USD/Barrel", "period": "Datum"})
    fig.write_html(PLOT_DAILY)
    print(f"📊 Plot gespeichert: {PLOT_DAILY}")

    last  = float(df["brent_futures_usd"].iloc[-1])
    prev  = float(df["brent_futures_usd"].iloc[-2])
    trend = "↑" if last > prev else ("↓" if last < prev else "→")
    berlin = pytz.timezone("Europe/Berlin")

    return {
        "last_price": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }


# ── 2) Intraday stündlich ────────────────────────────────────────────────────

def fetch_intraday() -> pd.DataFrame:
    """
    Stündliche Schlusskurse Brent Crude Oil Futures (BZ=F).
    Quelle: Yahoo Finance via yfinance
    Verfügbarkeit: maximal letzte 60 Tage
    Spalte: brent_futures_usd_1h (USD/Barrel, Close)
    """
    ticker = yf.Ticker("BZ=F")
    raw = ticker.history(period="60d", interval="1h", auto_adjust=True)

    if raw.empty:
        raise ValueError("yfinance hat keine Intraday-Daten zurückgegeben.")

    df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "period"
    df = df.rename(columns={"Close": "brent_futures_usd_1h"})
    df = df.dropna()
    return df


def update_intraday() -> dict:
    """Intraday: neue Stunden an bestehende CSV anhängen (append)."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("plots", exist_ok=True)

    try:
        df_new = fetch_intraday()
    except Exception as e:
        print(f"❌ yfinance stündlich fehlgeschlagen: {e}")
        return {}

    if os.path.exists(CSV_INTRADAY):
        df_existing = pd.read_csv(CSV_INTRADAY, index_col=0, parse_dates=True)
        df_existing.index.name = "period"
        last_ts = df_existing.index[-1]
        df_append = df_new[df_new.index > last_ts]

        if df_append.empty:
            print("ℹ️  Intraday: keine neuen Daten.")
            df = df_existing
        else:
            df = pd.concat([df_existing, df_append]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
            print(f"✅ yfinance stündlich (BZ=F): {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        df = df_new
        print(f"✅ yfinance stündlich (BZ=F): {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    df.to_csv(CSV_INTRADAY)
    print(f"📄 CSV gespeichert: {CSV_INTRADAY}")

    fig = px.line(df, x=df.index, y="brent_futures_usd_1h",
                  title="Brent Crude Oil Futures (BZ=F) — stündlich | Quelle: Yahoo Finance",
                  labels={"brent_futures_usd_1h": "USD/Barrel", "period": "Datum"})
    fig.write_html(PLOT_INTRADAY)
    print(f"📊 Plot gespeichert: {PLOT_INTRADAY}")

    last  = float(df["brent_futures_usd_1h"].iloc[-1])
    prev  = float(df["brent_futures_usd_1h"].iloc[-2])
    trend = "↑" if last > prev else ("↓" if last < prev else "→")
    berlin = pytz.timezone("Europe/Berlin")

    return {
        "last_price": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y %H:%M"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("─── Tagesdaten (yfinance BZ=F) ───")
    stats_daily = update_daily()
    if stats_daily:
        print(f"🛢  Brent täglich:   {stats_daily['last_price']:.2f} USD {stats_daily['trend']} "
              f"(Stand: {stats_daily['last_date']}) | {stats_daily['rows']} Zeilen")

    print("\n─── Intraday stündlich (yfinance BZ=F) ───")
    stats_intraday = update_intraday()
    if stats_intraday:
        print(f"🛢  Brent stündlich: {stats_intraday['last_price']:.2f} USD {stats_intraday['trend']} "
              f"(Stand: {stats_intraday['last_date']}) | {stats_intraday['rows']} Zeilen")

    if "GITHUB_OUTPUT" in os.environ and stats_daily:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_price={stats_daily['last_price']}\n")
            f.write(f"trend={stats_daily['trend']}\n")
            f.write(f"updated={stats_daily['updated']}\n")