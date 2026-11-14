import streamlit as st
import pandas as pd

# Configurazione della pagina
st.set_page_config(page_title="LD2410C IoT Dashboard", page_icon="📡", layout="wide")

st.title("📡 Monitoraggio Presenze & Radar LD2410C")
st.markdown("Dashboard in tempo reale collegata al sistema IoT (ESP8266 + ESP32 Gateway + Google Sheets).")

# Funzione per caricare i dati dal Google Sheet pubblico
@st.cache_data(ttl=10)
def load_data():
    sheet_id = "1jlR5DCBZQqTjkePk7SWaH380RehClI1wFANYeWICu8c"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    df = pd.read_csv(url)
    return df

try:
    df = load_data()

    # Mostra un avviso se il DataFrame è vuoto o ha solo le intestazioni
    if df.empty or len(df.columns) == 0:
        st.warning("Il foglio Google Sheets è attualmente vuoto o in attesa di dati dal sensore.")
    else:
        # Pulisce i nomi delle colonne da spazi indesiderati
        df.columns = df.columns.str.strip()
        
        # Mostra le metriche basate sull'ultima riga disponibile
        ultima_riga = df.iloc[-1]
        
        st.subheader("Ultimo Stato Rilevato")
        col1, col2, col3, col4 = st.columns(4)
        
        # Mostriamo le colonne in base al loro indice per sicurezza
        col_names = list(df.columns)
        
        with col1:
            val_presenza = ultima_riga.iloc[1] if len(col_names) > 1 else "N/D"
            st.metric("Stato Rilevamento", val_presenza)
            
        with col2:
            val_dist = ultima_riga.iloc[2] if len(col_names) > 2 else "N/D"
            st.metric("Distanza Target", f"{val_dist} cm")
            
        with col3:
            val_mov = ultima_riga.iloc[3] if len(col_names) > 3 else "N/D"
            st.metric("Energia Moving", val_mov)
            
        with col4:
            val_stat = ultima_riga.iloc[4] if len(col_names) > 4 else "N/D"
            st.metric("Energia Static", val_stat)

        st.divider()

        # Sezione Grafici Interattivi (se ci sono abbastanza colonne numeriche)
        if len(col_names) >= 5:
            st.subheader("📊 Storico Energia Target (Moving & Static)")
            st.line_chart(df[[col_names[3], col_names[4]]], height=300)

            st.subheader("📉 Storico Distanza Rilevata")
            st.line_chart(df[[col_names[2]]], height=250)

        # Tabella dati grezzi
        with st.expander("🔍 Visualizza tabella dati grezzi (ultimi record)"):
            st.dataframe(df.tail(50), use_container_width=True)

except Exception as e:
    st.error(f"Errore nel caricamento o elaborazione dei dati: {e}")

# Pulsante per forzare il refresh manuale
if st.button("🔄 Aggiorna Dati"):
    st.rerun()
