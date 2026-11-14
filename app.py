import streamlit as st
import pandas as pd

# Configurazione della pagina
st.set_page_config(page_title="LD2410C IoT Dashboard", page_icon="📡", layout="wide")

st.title("📡 Monitoraggio Presenze & Radar LD2410C")
st.markdown("Dashboard in tempo reale collegata al sistema IoT (ESP8266 + ESP32 Gateway + Google Sheets).")

# Portata massima configurata sul sensore LD2410C (in cm)
MAX_RANGE_CM = 600.0

# Funzione per caricare i dati dal Google Sheet pubblico
@st.cache_data(ttl=10)
def load_data():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTW9W95wvrqKa3ArJlvvQJAb1k1GYVf5e98D-JacPJRY536AHFRVxxTRb6XPmjaZ5ZdP5sm8rzstXon/pub?gid=0&single=true&output=csv"
    df = pd.read_csv(url)
    return df

try:
    df = load_data()

    if df.empty or len(df.columns) == 0:
        st.warning("Il foglio Google Sheets è attualmente vuoto o in attesa di dati dal sensore.")
    else:
        # Pulisce i nomi delle colonne da spazi indesiderati
        df.columns = df.columns.str.strip()
        ultima_riga = df.iloc[-1]
        col_names = list(df.columns)

        st.subheader("Ultimo Stato Rilevato")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            val_presenza = ultima_riga.iloc[1] if len(col_names) > 1 else "N/D"
            st.metric("Stato Rilevamento", val_presenza)

        with col2:
            val_dist = ultima_riga.iloc[2] if len(col_names) > 2 else 0
            st.metric("Distanza Target", f"{val_dist} cm")

        with col3:
            val_mov = ultima_riga.iloc[3] if len(col_names) > 3 else "N/D"
            st.metric("Energia Moving", val_mov)

        with col4:
            val_stat = ultima_riga.iloc[4] if len(col_names) > 4 else "N/D"
            st.metric("Energia Static", val_stat)

        # --- INDICATORE VISIVO DI PROSSIMITÀ (GAUGE) ---
        st.markdown("### 🎯 Indicatore di Prossimità Radar")
        try:
            distanza_num = float(val_dist)
            presenza_num = int(float(val_presenza)) if val_presenza != "N/D" else 0

            if presenza_num == 0 or distanza_num <= 0:
                progresso = 0.0
                stato_zona = "⚪ Nessun target nel raggio d'azione"
            else:
                progresso = min(max(distanza_num / MAX_RANGE_CM, 0.0), 1.0)
                if distanza_num < 100:
                    stato_zona = f"🔴 Rilevamento ravvicinato ({int(distanza_num)} cm / {int(MAX_RANGE_CM)} cm)"
                elif distanza_num < 300:
                    stato_zona = f"🟠 Media distanza ({int(distanza_num)} cm / {int(MAX_RANGE_CM)} cm)"
                else:
                    stato_zona = f"🟢 Lunga distanza ({int(distanza_num)} cm / {int(MAX_RANGE_CM)} cm)"

            st.progress(progresso, text=stato_zona)
        except (ValueError, TypeError):
            st.info("In attesa di valori numerici validi per la distanza.")

        st.divider()

        # Sezione Grafici Interattivi
        if len(col_names) >= 5:
            st.subheader("📊 Storico Energia Target (Moving & Static)")
            st.line_chart(df[[col_names[3], col_names[4]]], height=300)

            st.subheader("🎯 Grafico a Dispersione: Distanza & Presenza nel Tempo")
            df_chart = df.copy()
            df_chart[col_names[2]] = pd.to_numeric(df_chart[col_names[2]], errors='coerce')
            df_chart[col_names[1]] = pd.to_numeric(df_chart[col_names[1]], errors='coerce')

            st.scatter_chart(
                df_chart,
                y=col_names[2],
                color=col_names[1],
                height=300
            )

        # Tabella dati grezzi
        with st.expander("🔍 Visualizza tabella dati grezzi (ultimi record)"):
            st.dataframe(df.tail(50), use_container_width=True)

except Exception as e:
    st.error(f"Errore nel caricamento o elaborazione dei dati: {e}")

# Pulsante per forzare il refresh manuale
if st.button("🔄 Aggiorna Dati"):
    st.rerun()
