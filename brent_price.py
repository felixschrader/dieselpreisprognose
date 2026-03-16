# oil_analysis.py
import pandas as pd
from pandas_datareader import data as pdr
from datetime import datetime
import os
import plotly.express as px
import json
from dotenv import load_dotenv

# .env Datei laden
load_dotenv()

def update_oil_data():
    # API-Key aus Umgebungsvariablen
    FRED_API_KEY = os.getenv("FRED_API_KEY")
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY nicht in .env gesetzt!")

    # Daten laden
    oil_data = pdr.DataReader("DCOILBRENTEU", "fred", start="2014-01-01")

    # Verzeichnisse erstellen
    os.makedirs("data", exist_ok=True)
    os.makedirs("plots", exist_ok=True)

    # Daten speichern
    oil_data.to_csv("data/brent_oil_prices.csv")

    # Monatsdurchschnitt
    monthly_avg = oil_data.resample('M').mean()
    monthly_avg.to_csv("data/brent_oil_monthly.csv")

    # Statistiken
    stats = {
        "last_price": float(oil_data.iloc[-1]["DCOILBRENTEU"]),
        "updated": datetime.today().strftime("%Y-%m-%d")
    }
    with open("data/stats.json", "w") as f:
        json.dump(stats, f)

    # Plot erstellen
    fig = px.line(oil_data, x=oil_data.index, y="DCOILBRENTEU",
                 title="Brent Ölpreis 2014–heute")
    fig.write_html("plots/oil_price.html")

    
    stats = {
        "last_price": float(oil_data.iloc[-1]["DCOILBRENTEU"]),
        "trend": "steigend" if oil_data.iloc[-1]["DCOILBRENTEU"] > oil_data.iloc[-30]["DCOILBRENTEU"] else "fallend",
        "updated": datetime.today().strftime("%Y-%m-%d %H:%M")
    }

    # Für GitHub Actions Output
    print(f"::set-output name=last_price::{stats['last_price']}")
    print(f"::set-output name=trend::{stats['trend']}")

    return stats

if __name__ == "__main__":
    stats = update_oil_data()
    print("✅ Daten erfolgreich aktualisiert!")
    print(json.dumps(stats, indent=2))
