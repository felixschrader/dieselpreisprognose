# Seite 6 — Einflussfaktoren
import streamlit as st
import plotly.express as px
from pathlib import Path
from page_data import get_page_data
from figure_cache import get_cached_figure

df = get_page_data(
    required_columns={"preis", "ist_wochenende", "sonnenstunden", "schulferien_name"}
)

#st.title("Prognose von Benzinpreisen")

st.header("🌤 Einflussfaktoren")

# KPI
col1, col2, col3, col4 = st.columns(4)
col1.metric("Wochenende Ø", round(df[df["ist_wochenende"]==1]["preis"].mean(),3))
col2.metric("Werktag Ø", round(df[df["ist_wochenende"]==0]["preis"].mean(),3))
col3.metric("Max Sonne", df["sonnenstunden"].max())
col4.metric("Ferientage", df["schulferien_name"].notna().sum())

col1, col2 = st.columns(2)

with col1:
    fig = get_cached_figure(
        "06",
        "bar_wochenende",
        lambda: px.bar(df.groupby("ist_wochenende")["preis"].mean().reset_index(), x="ist_wochenende", y="preis"),
    )
    st.plotly_chart(fig)
    st.caption("Wochenende Einfluss")

with col2:
    fig2 = get_cached_figure("06", "scatter_sonne", lambda: px.scatter(df, x="sonnenstunden", y="preis"))
    st.plotly_chart(fig2)
    st.caption("Sonne Einfluss")



img_path = Path(__file__).resolve().parents[1] / "images" / "image.png"
if img_path.exists():
    st.image(str(img_path))