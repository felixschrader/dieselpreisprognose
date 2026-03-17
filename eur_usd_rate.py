# =============================================================================
# eur_usd_rate.py
# Lädt tägliche EUR/USD Wechselkurse von der Europäischen Zentralbank (EZB)
# und speichert sie als CSV.
#
# Quelle: EZB Statistical Data Warehouse (SDW) API — kostenlos, kein API-Key
# Frequenz: täglich (Handelstage), offizieller EZB-Referenzkurs
# Einheit: USD pro 1 EUR (z.B. 1.15 = 1 Euro kostet 1,15 Dollar)
#
# Warum EUR/USD als Feature?
#   Rohöl wird global in USD gehandelt. Wenn der Euro stärker wird,
#   wird Öl für europäische Käufer günstiger — das beeinflusst Tankstellenpreise.
# =============================================================================

# requests: Bibliothek für HTTP-Anfragen — damit rufen wir die EZB-API auf
import requests

# pandas: Standard-Bibliothek für Tabellen (DataFrames)
import pandas as pd

# io: Input/Output-Hilfsmittel — hier um einen Text-String wie eine Datei zu lesen
# (die EZB liefert CSV als Text, pd.read_csv erwartet aber normalerweise eine Datei)
import io

# os: Betriebssystem-Funktionen — Ordner anlegen, Dateipfade prüfen
import os

# datetime: Datum und Uhrzeit für Zeitstempel im Output
from datetime import datetime

# pytz: Zeitzonen — stellt sicher dass wir Berliner Zeit ausgeben
import pytz


# =============================================================================
# Konfiguration
# =============================================================================

# Pfad zur CSV-Datei
CSV_PATH = "data/eur_usd_rate.csv"

# EZB API-Endpunkt:
# D = Daily (täglich)
# USD.EUR = USD zu EUR
# SP00 = Spot-Kurs (aktueller Marktkurs, kein Termin-/Futures-Kurs)
# A = Average (Durchschnitt des Handelstages)
EZB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata"


# =============================================================================
# DATEN HOLEN
# =============================================================================

def fetch_eur_usd() -> pd.DataFrame:
    """
    Lädt alle verfügbaren EUR/USD Tageskurse von der EZB API.
    Die EZB liefert immer den kompletten historischen Datensatz in einem Request.
    Gibt einen DataFrame zurück mit Datum als Index und Kurs als Spalte.
    """
    # HTTP GET-Anfrage an die EZB API
    # timeout=10: nach 10 Sekunden abbrechen wenn keine Antwort kommt
    r = requests.get(EZB_URL, timeout=10)

    # Fehler werfen wenn HTTP-Statuscode nicht 200 (OK) ist
    r.raise_for_status()

    # Die Antwort ist ein CSV-Text — io.StringIO macht daraus ein datei-ähnliches Objekt
    # damit pd.read_csv damit umgehen kann
    df = pd.read_csv(io.StringIO(r.text))

    # Nur die relevanten Spalten behalten: Datum und Kurs
    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()

    # Spalten umbenennen: klar und einheitlich
    df.columns = ["date", "eur_usd"]

    # Datum-Strings in echte Datum-Objekte umwandeln (z.B. "2024-01-15" → Timestamp)
    df["date"] = pd.to_datetime(df["date"])

    # Kurswerte in Zahlen umwandeln — errors="coerce" macht fehlerhafte Werte zu NaN
    # statt einen Fehler zu werfen
    df["eur_usd"] = pd.to_numeric(df["eur_usd"], errors="coerce")

    # Nach Datum sortieren (älteste zuerst) und fehlende Kurse entfernen
    df = df.sort_values("date").dropna(subset=["eur_usd"])

    # Datum als Index setzen — einheitlich mit anderen Datensätzen im Projekt
    df = df.set_index("date")
    df.index.name = "period"

    return df


# =============================================================================
# CSV AKTUALISIEREN
# =============================================================================

def update_eur_usd() -> dict:
    """
    Aktualisiert die EUR/USD CSV — hängt nur neue Daten an, überschreibt nichts.

    Logik:
    - CSV existiert bereits → nur Zeilen neuer als letzter Datenpunkt anhängen
    - CSV existiert noch nicht → kompletter Datensatz wird gespeichert
    """
    # Ordner anlegen falls noch nicht vorhanden
    os.makedirs("data", exist_ok=True)

    # Daten von der EZB holen
    try:
        df_new = fetch_eur_usd()
    except Exception as e:
        print(f"❌ EZB-Abruf fehlgeschlagen: {e}")
        return {}  # Leeres Dict = kein Absturz, aber auch kein Update

    if os.path.exists(CSV_PATH):
        # Bestehende CSV laden
        df_existing = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True)
        df_existing.index.name = "period"

        # Letzten bekannten Datenpunkt ermitteln
        last_ts = df_existing.index[-1]

        # Nur neue Zeilen (neuer als letzter gespeicherter Kurs)
        df_append = df_new[df_new.index > last_ts]

        if df_append.empty:
            # Nichts Neues — CSV bleibt wie sie ist
            print("ℹ️  EUR/USD: keine neuen Daten.")
            df = df_existing
        else:
            # Alte und neue Daten zusammenführen
            df = pd.concat([df_existing, df_append]).sort_index()

            # Doppelte Einträge entfernen (Sicherheitsnetz)
            df = df[~df.index.duplicated(keep="last")]

            print(f"✅ EZB EUR/USD: {len(df_append)} neue Datenpunkte "
                  f"(gesamt: {len(df)})")
    else:
        # Erster Download — gesamten Datensatz speichern
        df = df_new
        print(f"✅ EZB EUR/USD: {len(df)} Datenpunkte "
              f"({df.index[0].date()} – {df.index[-1].date()})")

    # CSV speichern
    df.to_csv(CSV_PATH)
    print(f"📄 CSV gespeichert: {CSV_PATH}")

    # Letzten und vorletzten Kurs für Trendpfeil
    last  = float(df["eur_usd"].iloc[-1])   # iloc[-1] = letzte Zeile
    prev  = float(df["eur_usd"].iloc[-2])   # iloc[-2] = vorletzte Zeile
    trend = "↑" if last > prev else ("↓" if last < prev else "→")

    # Berliner Zeitzone für den Zeitstempel
    berlin = pytz.timezone("Europe/Berlin")

    stats = {
        "last_rate": last,
        "trend": trend,
        "last_date": df.index[-1].strftime("%d.%m.%Y"),
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "rows": len(df),
    }

    # GitHub Actions: Ergebnisse als Output-Variablen weitergeben
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_rate={stats['last_rate']}\n")
            f.write(f"trend={stats['trend']}\n")
            f.write(f"updated={stats['updated']}\n")

    return stats


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    stats = update_eur_usd()
    if stats:
        print(f"💱 EUR/USD: {stats['last_rate']:.4f} {stats['trend']} "
              f"(Stand: {stats['last_date']}) | aktualisiert: {stats['updated']} "
              f"| {stats['rows']} Zeilen")