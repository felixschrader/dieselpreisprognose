# =============================================================================
# brent_price.py
# Lädt Brent-Rohölpreise (Futures) von Yahoo Finance und speichert sie als CSV.
#
# Quelle: Yahoo Finance — Brent Crude Oil Last Day Financial Futures (BZ=F)
# Börse:  NY Mercantile (NYMEX), cash-settled (Abrechnung in Cash, kein echtes Öl)
# Einheit: USD/Barrel
#
# Zwei Datensätze:
#   - Tagesdaten:  historisch seit 2014-01-01, unbegrenzt verfügbar
#   - Intraday:    stündlich, maximal letzte 60 Tage (Yahoo Finance Limit)
#
# Warum Futures statt Spot-Preis?
#   Futures sind tagesaktuell und enthalten bereits Markterwartungen.
#   Tankstellen orientieren sich an Markterwartungen, nicht am gestrigen Spot.
#   Offizielle Spot-Daten (EIA, FRED) haben außerdem oft 1 Woche Verzögerung.
# =============================================================================

# yfinance: Python-Bibliothek um Finanzdaten von Yahoo Finance herunterzuladen
# Kein API-Key nötig, kostenlos
import yfinance as yf

# pandas: die Standard-Bibliothek für Tabellen (DataFrames) in Python
# Wird hier für alles genutzt: Daten laden, filtern, zusammenführen, speichern
import pandas as pd

# os: Betriebssystem-Funktionen — hier für Dateipfade und Ordner anlegen
import os

# datetime: Datum und Uhrzeit — hier für Zeitstempel im Output
from datetime import datetime

# pytz: Zeitzonen-Bibliothek — stellt sicher dass wir Berliner Zeit ausgeben
# (nicht UTC, was der Server-Standard wäre)
import pytz


# =============================================================================
# Konfiguration — Pfade und Startdatum
# Alles an einem Ort, damit man nichts suchen muss wenn man etwas ändern will
# =============================================================================

CSV_DAILY    = "data/brent_futures_daily.csv"        # Tägliche Daten
CSV_INTRADAY = "data/brent_futures_intraday_1h.csv"  # Stündliche Daten
HISTORY_START = "2014-01-01"                          # Startdatum für den initialen Download


# =============================================================================
# 1) TAGESDATEN
# =============================================================================

def fetch_daily(start: str) -> pd.DataFrame:
    """
    Holt tägliche Schlusskurse (Close) von Yahoo Finance ab einem bestimmten Datum.

    'start' ist ein Datum als String, z.B. "2014-01-01".
    Gibt einen DataFrame zurück: eine Tabelle mit Datum als Index und Preis als Spalte.
    """
    # Ticker-Objekt erstellen — "BZ=F" ist das Yahoo-Finance-Kürzel für Brent Futures
    ticker = yf.Ticker("BZ=F")

    # Historische Daten abrufen:
    # - start: ab diesem Datum
    # - interval="1d": einen Datenpunkt pro Tag
    # - auto_adjust=True: Preise werden automatisch um Dividenden/Splits bereinigt
    raw = ticker.history(start=start, interval="1d", auto_adjust=True)

    # Sicherheitscheck: wenn keine Daten kamen, Fehler werfen
    if raw.empty:
        raise ValueError("yfinance hat keine Tagesdaten zurückgegeben.")

    # Nur die Schlusskurs-Spalte behalten, Rest wegwerfen
    df = raw[["Close"]].copy()

    # Zeitzone entfernen (Yahoo liefert UTC, wir wollen naive Timestamps)
    df.index = pd.to_datetime(df.index).tz_localize(None)

    # Index (Datumspalte) umbenennen — einheitlich mit anderen Datensätzen im Projekt
    df.index.name = "period"

    # Spalte umbenennen: "Close" → "brent_futures_usd" — klar erkennbar was drin steckt
    df = df.rename(columns={"Close": "brent_futures_usd"})

    # Zeilen mit fehlenden Werten entfernen (z.B. Wochenenden ohne Handel)
    df = df.dropna()

    return df


def update_daily() -> dict:
    """
    Aktualisiert die Tages-CSV — hängt nur neue Daten an, überschreibt nichts.

    Logik:
    - CSV existiert bereits → nur ab letztem Datenpunkt nachladen (append)
    - CSV existiert noch nicht → kompletter Download seit HISTORY_START
    """
    # Ordner anlegen falls noch nicht vorhanden (exist_ok=True = kein Fehler wenn schon da)
    os.makedirs("data", exist_ok=True)

    # Prüfen ob CSV schon existiert
    if os.path.exists(CSV_DAILY):
        # Bestehende CSV laden — index_col=0 setzt die erste Spalte als Index
        # parse_dates=True wandelt den Index automatisch in Datum-Objekte um
        df_existing = pd.read_csv(CSV_DAILY, index_col=0, parse_dates=True)
        df_existing.index.name = "period"

        # Letzten bekannten Datenpunkt ermitteln
        last_ts = df_existing.index[-1]

        # Ab diesem Datum bei Yahoo anfragen (nicht komplett neu laden)
        fetch_start = last_ts.strftime("%Y-%m-%d")
    else:
        # Noch keine CSV → kompletter Download
        df_existing = None
        fetch_start = HISTORY_START

    # Daten von Yahoo holen
    try:
        df_new = fetch_daily(start=fetch_start)
    except Exception as e:
        print(f"❌ yfinance täglich fehlgeschlagen: {e}")
        return {}  # Leeres Dict zurückgeben = kein Absturz, aber auch kein Update

    if df_existing is not None:
        # Nur Zeilen die neuer sind als der letzte bekannte Datenpunkt
        df_append = df_new[df_new.index > df_existing.index[-1]]

        if df_append.empty:
            # Nichts Neues — CSV bleibt wie sie ist
            print("ℹ️  Tagesdaten: keine neuen Daten.")
            df = df_existing
        else:
            # Alte und neue Daten zusammenführen
            df = pd.concat([df_existing, df_append]).sort_index()

            # Doppelte Zeilen entfernen (kann passieren wenn Datum überschneidet)
            df = df[~df.index.duplicated(keep="last")]

            print(f"✅ yfinance täglich (BZ=F): {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        # Erster Download — alles ist neu
        df = df_new
        print(f"✅ yfinance täglich (BZ=F): {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    # CSV speichern (überschreibt die alte komplett, aber mit allen Daten drin)
    df.to_csv(CSV_DAILY)
    print(f"📄 CSV gespeichert: {CSV_DAILY}")

    # Letzten und vorletzten Preis für Trendpfeil ermitteln
    last  = float(df["brent_futures_usd"].iloc[-1])   # iloc[-1] = letzte Zeile
    prev  = float(df["brent_futures_usd"].iloc[-2])   # iloc[-2] = vorletzte Zeile
    trend = "↑" if last > prev else ("↓" if last < prev else "→")

    # Berliner Zeitzone für den Zeitstempel im Output
    berlin = pytz.timezone("Europe/Berlin")

    # Ergebnis als Dictionary zurückgeben (wird im Main-Block ausgegeben
    # und optional an GitHub Actions weitergegeben)
    return {
        "last_price": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }


# =============================================================================
# 2) INTRADAY (stündlich)
# =============================================================================

def fetch_intraday() -> pd.DataFrame:
    """
    Holt stündliche Schlusskurse der letzten 60 Tage von Yahoo Finance.
    60 Tage ist das Maximum das Yahoo Finance für stündliche Daten erlaubt.
    """
    ticker = yf.Ticker("BZ=F")

    # period="60d": die letzten 60 Tage
    # interval="1h": ein Datenpunkt pro Stunde
    raw = ticker.history(period="60d", interval="1h", auto_adjust=True)

    if raw.empty:
        raise ValueError("yfinance hat keine Intraday-Daten zurückgegeben.")

    df = raw[["Close"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.index.name = "period"
    df = df.rename(columns={"Close": "brent_futures_usd_1h"})  # _1h = stündlich
    df = df.dropna()

    return df


def update_intraday() -> dict:
    """
    Aktualisiert die Intraday-CSV — hängt nur neue Stunden an, überschreibt nichts.
    Gleiche Logik wie update_daily(), nur für stündliche Daten.
    """
    os.makedirs("data", exist_ok=True)

    try:
        df_new = fetch_intraday()
    except Exception as e:
        print(f"❌ yfinance stündlich fehlgeschlagen: {e}")
        return {}

    if os.path.exists(CSV_INTRADAY):
        df_existing = pd.read_csv(CSV_INTRADAY, index_col=0, parse_dates=True)
        df_existing.index.name = "period"
        last_ts = df_existing.index[-1]

        # Nur Stunden die neuer sind als der letzte gespeicherte Zeitstempel
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


# =============================================================================
# MAIN — wird nur ausgeführt wenn das Skript direkt gestartet wird
# (nicht wenn es von einem anderen Skript importiert wird)
# =============================================================================

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

    # GitHub Actions: Ergebnisse als Output-Variablen weitergeben
    # (wird im Workflow-YAML als ${{ steps.xxx.outputs.last_price }} verwendet)
    if "GITHUB_OUTPUT" in os.environ and stats_daily:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_price={stats_daily['last_price']}\n")
            f.write(f"trend={stats_daily['trend']}\n")
            f.write(f"updated={stats_daily['updated']}\n")