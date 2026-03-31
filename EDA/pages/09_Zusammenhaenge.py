# Seite 9 — Zusammenhänge
import streamlit as st
import plotly.express as px
from page_data import get_page_data
from figure_cache import get_cached_figure

df = get_page_data(
    required_columns={"preis", "temp_avg", "niederschlag_mm", "co2_preis_eur_t", "eur_usd"}
)

#st.title("Prognose von Benzinpreisen")

st.header("🔗 Preisveränderung & Beziehungen")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Temp Corr", round(df["preis"].corr(df["temp_avg"]),2))
col2.metric("Regen Corr", round(df["preis"].corr(df["niederschlag_mm"]),2))
col3.metric("CO2 Corr", round(df["preis"].corr(df["co2_preis_eur_t"]),2))
col4.metric("EUR/USD Corr", round(df["preis"].corr(df["eur_usd"]),2))

col1, col2 = st.columns(2)

with col1:
    fig = get_cached_figure("09", "scatter_temp", lambda: px.scatter(df, x="temp_avg", y="preis"))
    st.plotly_chart(fig)
    st.caption("Temperatur")

with col2:
    fig2 = get_cached_figure(
        "09",
        "scatter_regen",
        lambda: px.scatter(df, x="niederschlag_mm", y="preis"),
    )
    st.plotly_chart(fig2)
    st.caption("Regen")