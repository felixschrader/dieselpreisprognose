# Seite 4 — Markenvergleich
import streamlit as st
import plotly.express as px
from page_data import get_page_data
from figure_cache import get_cached_figure

df = get_page_data(required_columns={"preis", "brand"})

#st.title("Prognose von Benzinpreisen")

st.header("⛽ Welche Marke ist günstiger?")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Marken", df["brand"].nunique())
col2.metric("Günstigste", df.groupby("brand")["preis"].mean().idxmin())
col3.metric("Teuerste", df.groupby("brand")["preis"].mean().idxmax())
col4.metric("Ø Preis", round(df["preis"].mean(),3))

col1, col2 = st.columns(2)

with col1:
    fig = get_cached_figure(
        "04",
        "bar_brand",
        lambda: px.bar(df.groupby("brand")["preis"].mean().reset_index(), x="brand", y="preis"),
    )
    st.plotly_chart(fig)
    st.caption("Durchschnittspreis je Marke")

with col2:
    fig2 = get_cached_figure("04", "box_brand", lambda: px.box(df, x="brand", y="preis"))
    st.plotly_chart(fig2)
    st.caption("Preisverteilung")