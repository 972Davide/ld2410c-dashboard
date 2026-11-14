import streamlit as st
import pandas as pd
import plotly.express as px

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

        # --- SEZIONE 4 GRAFICI PLOTLY PROFESSIONALI (GRIGLIA 2x2) ---
        if len(col_names) >= 5:
            st.subheader("📈 Analisi Dettagliata (Grafici Avanzati)")

            df_chart = df.copy()
            for c_idx in [1, 2, 3, 4]:
                if len(col_names) > c_idx:
                    df_chart[col_names[c_idx]] = pd.to_numeric(df_chart[col_names[c_idx]], errors='coerce')

            # Creiamo una colonna temporale fittizia o usiamo l'indice come asse X pulito
            df_chart['Index'] = df_chart.reset_index().index

            g_col1, g_col2 = st.columns(2)

            with g_col1:
                # 1. Distanza
                fig1 = px.line(df_chart, x='Index', y=col_names[2], title=f"📍 {col_names[2]} (cm)", template="plotly_dark")
                fig1.update_traces(line_color='#00ffcc', line_width=2)
                fig1.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig1, use_container_width=True)

                # 3. Energia Static
                fig3 = px.line(df_chart, x='Index', y=col_names[4], title=f"🧘 {col_names[4]}", template="plotly_dark")
                fig3.update_traces(line_color='#ff00ff', line_width=2)
                fig3.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig3, use_container_width=True)

            with g_col2:
                # 2. Energia Moving
                fig2 = px.line(df_chart, x='Index', y=col_names[3], title=f"🚶 {col_names[3]}", template="plotly_dark")
                fig2.update_traces(line_color='#ff9900', line_width=2)
                fig2.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig2, use_container_width=True)

                # 4. Stato Rilevamento
                fig4 = px.line(df_chart, x='Index', y=col_names[1], title=f"👁️ {col_names[1]}", template="plotly_dark")
                fig4.update_traces(line_color='#3399ff', line_width=2)
                fig4.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig4, use_container_width=True)

        # Tabella dati grezzi
        with st.expander("🔍 Visualizza tabella dati grezzi (ultimi record)"):
            st.dataframe(df.tail(50), use_container_width=True)

except Exception as e:
    st.error(f"Errore nel caricamento o elaborazione dei dati: {e}")

# Pulsante per forzare il refresh manuale
if st.button("🔄 Aggiorna Dati"):
    st.rerun()
