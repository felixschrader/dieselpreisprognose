import requests
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
import pytz
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")

AV_URL = "https://www.alphavantage.co/query"


def fetch_brent_from_alphavantage(start: str = "2014-01-01") -> pd.DataFrame:
    """
    Lädt tagesaktuelle Brent Crude Spot-Preise von Alpha Vantage.
    Kein Futures-Kontrakt, echter Spot-Preis (WTI/Brent).

    Parameter
    ---------
    start : str
        Startdatum im Format YYYY-MM-DD (default: 2014-01-01)

    Returns
    -------
    pd.DataFrame mit DatetimeIndex (name='period') und Spalte 'DCOILBRENTEU'
    """
    if not ALPHA_VANTAGE_KEY:
        raise EnvironmentError(
            "ALPHA_VANTAGE_KEY nicht gesetzt. "
            "Lokal: in .env eintragen. "
            "GitHub: als Repository Secret hinterlegen."
        )

    params = {
        "function": "BRENT",
        "interval": "daily",
        "datatype": "json",
        "apikey": ALPHA_VANTAGE_KEY,
    }

    r = requests.get(AV_URL, params=params, timeout=15)
    r.raise_for_status()
    payload = r.json()

    if "data" not in payload:
        raise ValueError(f"Unerwartete API-Antwort: {payload}")

    df = pd.DataFrame(payload["data"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df.index.name = "period"
    df = df.rename(columns={"value": "DCOILBRENTEU"})
    df["DCOILBRENTEU"] = pd.to_numeric(df["DCOILBRENTEU"], errors="coerce")
    df = df.dropna()

    # Auf Startdatum filtern
    df = df[df.index >= pd.Timestamp(start)]

    return df


def update_brent_prices(start: str = "2014-01-01") -> dict:
    """
    Hauptfunktion: Daten laden, als CSV speichern, Plot generieren.
    Ersetzt den alten FRED/EIA-Export vollständig.
    """
    try:
        oil_data = fetch_brent_from_alphavantage(start=start)
        print(f"✅ Alpha Vantage: {len(oil_data)} Datenpunkte geladen "
              f"({oil_data.index[0].date()} – {oil_data.index[-1].date()})")
    except Exception as e:
        print(f"❌ Alpha Vantage-Abruf fehlgeschlagen: {e}")
        print("ℹ️  Fallback auf Testdaten")
        oil_data = pd.DataFrame(
            {"DCOILBRENTEU": [85.42, 86.10]},
            index=pd.DatetimeIndex(
                pd.date_range(start="2024-01-01", periods=2),
                name="period"
            ),
        )

    os.makedirs("data", exist_ok=True)
    os.makedirs("plots", exist_ok=True)

    csv_path = "data/brent_oil_prices.csv"
    oil_data.to_csv(csv_path)
    print(f"📄 CSV gespeichert: {csv_path}")

    fig = px.line(
        oil_data,
        x=oil_data.index,
        y="DCOILBRENTEU",
        title="Brent Rohölpreis (USD/Barrel) — Quelle: Alpha Vantage",
        labels={"DCOILBRENTEU": "USD/Barrel", "period": "Datum"},
    )
    plot_path = "plots/brent_prices.html"
    fig.write_html(plot_path)
    print(f"📊 Plot gespeichert: {plot_path}")

    berlin = pytz.timezone("Europe/Berlin")
    last = float(oil_data["DCOILBRENTEU"].iloc[-1])
    prev = float(oil_data["DCOILBRENTEU"].iloc[-2])
    trend = "↑" if last > prev else ("↓" if last < prev else "→")

    stats = {
        "last_price": last,
        "trend": trend,
        "updated": datetime.now(berlin).strftime("%d.%m.%Y %H:%M"),
        "last_date": oil_data.index[-1].strftime("%d.%m.%Y"),
        "rows": len(oil_data),
    }

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"last_price={stats['last_price']}\n")
            f.write(f"trend={stats['trend']}\n")
            f.write(f"updated={stats['updated']}\n")

    return stats


if __name__ == "__main__":
    stats = update_brent_prices()
    print(
        f"\n🛢  Brent: {stats['last_price']:.2f} USD/Barrel {stats['trend']} "
        f"(Stand: {stats['last_date']}) | aktualisiert: {stats['updated']}"
    )