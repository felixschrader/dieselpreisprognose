import pandas as pd
import streamlit as st

from data_loader import load_data


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    if "monat" not in out.columns and "timestamp" in out.columns:
        out["monat"] = out["timestamp"].dt.month
    if "stunde" not in out.columns and "timestamp" in out.columns:
        out["stunde"] = out["timestamp"].dt.hour
    if "tageszeit" not in out.columns and "stunde" in out.columns:
        out["tageszeit"] = pd.cut(
            out["stunde"],
            bins=[-1, 5, 11, 17, 23],
            labels=["Nacht", "Morgen", "Mittag", "Abend"],
        ).astype(str)
    if "preis" not in out.columns:
        fuel = st.session_state.get("fuel", "diesel")
        col = f"preis_{fuel}"
        if col in out.columns:
            out["preis"] = out[col]
        elif "preis_diesel" in out.columns:
            out["preis"] = out["preis_diesel"]
    return out


def get_page_data() -> pd.DataFrame:
    df = st.session_state.get("data")
    if df is None:
        df = load_data()
    df = _ensure_columns(df)
    st.session_state["data"] = df
    return df
