import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="LD2410C IoT Dashboard",
    page_icon="📡",
    layout="wide",
)

st.title("📡 Monitoraggio Presenze & Radar LD2410C")
st.markdown(
    "Dashboard in tempo reale collegata al sistema IoT "
    "(ESP8266 + ESP32 Gateway + Google Sheets)."
)

MAX_RANGE_CM = 600.0
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTW9W95wvrqKa3ArJlvvQJAb1k1GYVf5e98D-JacPJRY536AHFRVxxTRb6XPmjaZ5ZdP5sm8rzstXon/"
    "pub?gid=0&single=true&output=csv"
)

COLUMN_CANDIDATES = {
    "presence": ["presenza", "stato", "presence", "rilevamento"],
    "distance": ["distanza", "distance", "distanza_cm", "target_distance"],
    "moving": ["moving", "energia_moving", "moving_energy"],
    "static": ["static", "energia_static", "static_energy"],
}


# Fix 2: TTL cache allineato a 5 secondi
@st.cache_data(ttl=5, show_spinner=False)
def load_data():
    return pd.read_csv(SHEET_URL)


def find_column(df, candidates):
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def to_number(value, default=None):
    try:
        result = float(value)
        return result if pd.notna(result) else default
    except (TypeError, ValueError):
        return default


st.sidebar.header("⚙️ Impostazioni dashboard")

auto_refresh = st.sidebar.toggle(
    "🔄 Aggiornamento automatico",
    value=False,
)

refresh_seconds = st.sidebar.slider(
    "Intervallo aggiornamento (secondi)",
    min_value=5,
    max_value=120,
    value=15,
    step=5,
    disabled=not auto_refresh,
)

samples = st.sidebar.selectbox(
    "Campioni da visualizzare nei grafici",
    options=[200, 500, 1000, "Tutti"],
    index=1,
)

if st.sidebar.button("🔄 Aggiorna dati ora"):
    st.cache_data.clear()
    st.rerun()


@st.fragment(run_every=refresh_seconds if auto_refresh else None)
def radar_section():
    try:
        df = load_data()

        if df.empty:
            st.warning(
                "Il foglio Google Sheets è attualmente vuoto "
                "o in attesa di dati dal sensore."
            )
            return

        df.columns = df.columns.str.strip()

        cols = {
            key: find_column(df, candidates)
            for key, candidates in COLUMN_CANDIDATES.items()
        }

        missing = [key for key, col in cols.items() if col is None]
        if missing:
            st.warning(
                "Colonne non riconosciute: "
                + ", ".join(missing)
                + f". Colonne disponibili: {', '.join(df.columns)}"
            )

        last = df.iloc[-1]

        presence_value = (
            to_number(last[cols["presence"]], 0)
            if cols["presence"]
            else 0
        )

        distance_value = (
            to_number(last[cols["distance"]], 0)
            if cols["distance"]
            else 0
        )

        moving_value = last[cols["moving"]] if cols["moving"] else "N/D"
        static_value = last[cols["static"]] if cols["static"] else "N/D"

        st.subheader("Ultimo Stato Rilevato")
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Stato Rilevamento",
                "Presenza" if presence_value > 0 else "Assenza",
            )

        with c2:
            st.metric("Distanza Target", f"{distance_value:.0f} cm")

        with c3:
            st.metric("Energia Moving", moving_value)

        with c4:
            st.metric("Energia Static", static_value)

        st.markdown("### 🎯 Indicatore di Prossimità Radar")

        if presence_value <= 0 or distance_value <= 0:
            proximity = 0.0
            status = "⚪ Nessun target nel raggio d'azione"
        else:
            proximity = 1 - min(max(distance_value / MAX_RANGE_CM, 0.0), 1.0)

            if distance_value < 100:
                status = f"🔴 Rilevamento ravvicinato — {distance_value:.0f} cm"
            elif distance_value < 300:
                status = f"🟠 Media distanza — {distance_value:.0f} cm"
            else:
                status = f"🟢 Lunga distanza — {distance_value:.0f} cm"

        st.progress(proximity, text=status)

        st.divider()

        numeric_cols = [
            cols[key]
            for key in ["distance", "moving", "static"]
            if cols[key]
        ]

        df_chart = df.copy()

        for col in numeric_cols:
            df_chart[col] = pd.to_numeric(df_chart[col], errors="coerce")

        if cols["presence"]:
            df_chart[cols["presence"]] = pd.to_numeric(
                df_chart[cols["presence"]],
                errors="coerce",
            )

        if samples != "Tutti":
            df_chart = df_chart.tail(int(samples))

        # Fix 1 & Nota pratica: Ricerca, conversione e pulizia del timestamp
        time_col = find_column(
            df,
            [
                "timestamp",
                "data_ora",
                "data/ora",
                "time",
                "datetime",
                "data",
            ],
        )

        if time_col:
            df_chart[time_col] = pd.to_datetime(
                df_chart[time_col],
                errors="coerce",
            )
            df_chart = df_chart.dropna(subset=[time_col]).sort_values(time_col)
            x_col = time_col
        else:
            df_chart = df_chart.reset_index(drop=True)
            df_chart["Campione"] = df_chart.index + 1
            x_col = "Campione"

        if numeric_cols or cols["presence"]:
            st.subheader("📈 Analisi Dettagliata")

            left, right = st.columns(2)
            chart_specs = []

            if cols["distance"]:
                chart_specs.append(
                    (left, cols["distance"], "📍 Distanza target (cm)", "#00ffcc")
                )

            if cols["moving"]:
                chart_specs.append(
                    (right, cols["moving"], "🚶 Energia Moving", "#ff9900")
                )

            if cols["static"]:
                chart_specs.append(
                    (left, cols["static"], "🧘 Energia Static", "#ff00ff")
                )

            if cols["presence"]:
                chart_specs.append(
                    (right, cols["presence"], "👁️ Stato rilevamento", "#3399ff")
                )

            for container, y_col, title, color in chart_specs:
                fig = px.line(
                    df_chart,
                    x=x_col,
                    y=y_col,
                    title=title,
                    template="plotly_dark",
                )
                fig.update_traces(line_color=color, line_width=2)
                fig.update_layout(
                    height=280,
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                container.plotly_chart(fig, use_container_width=True)

        with st.expander("🔍 Visualizza tabella dati grezzi (ultimi record)"):
            st.dataframe(df.tail(50), use_container_width=True)

    except Exception as e:
        st.error(f"Errore nel caricamento o elaborazione dei dati: {e}")


radar_section()
