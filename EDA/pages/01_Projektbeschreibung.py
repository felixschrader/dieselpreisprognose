import streamlit as st

#st.title("Prognose von Benzinpreisen")

st.header("Projektziel")

st.write("""
Diese Anwendung analysiert die Entwicklung von Benzinpreisen
und beantwortet folgende Kernfragen:

- Wie entwickeln sich Preise?
- Wann tanke ich am günstigsten?
- Welche Tankstelle ist optimal?
- Welche Faktoren beeinflussen Preise?
""")

st.header("Datenbasis")

st.write("Dataset: ml_master_dataset.parquet")

st.header("Bedienung")

st.write("""
Filter befinden sich in der Sidebar.
Mehrere Visualisierungen pro Seite.
Interaktive Auswahl möglich.
""")

st.title("Prognose von Benzinpreisen")
st.write("Bitte Seite aus Navigation auswählen.")