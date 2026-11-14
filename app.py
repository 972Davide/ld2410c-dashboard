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
    "presence": [
        "presenza",
        "stato",
        "presence",
        "rilevamento",
    ],
    "distance": [
        "distanza",
        "distance",
        "distanza_cm",
        "target_distance",
    ],
    "moving": [
        "moving",
        "energia_moving",
        "moving_energy",
    ],
    "static": [
        "static",
        "energia_static",
        "static_energy",
    ],
}

TIME_COLUMN_CANDIDATES = [
    "timestamp",
    "data_ora",
    "data/ora",
    "time",
    "datetime",
    "data",
]


@st.cache_data(ttl=5, show_spinner=False)
def load_data():
    return pd.read_csv(SHEET_URL)


def find_column(df, candidates):
    normalized_columns = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        if candidate in normalized_columns:
            return normalized_columns[candidate]

    return None


def to_number(value, default=None):
    try:
        number = float(value)

        if pd.isna(number):
            return default

        return number

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

        columns = {
            key: find_column(df, candidates)
            for key, candidates in COLUMN_CANDIDATES.items()
        }

        missing_columns = [
            key
            for key, column in columns.items()
            if column is None
        ]

        if missing_columns:
            st.warning(
                "Colonne non riconosciute: "
                + ", ".join(missing_columns)
                + ". Colonne disponibili: "
                + ", ".join(df.columns)
            )

        last_row = df.iloc[-1]

        presence_value = (
            to_number(last_row[columns["presence"]], 0)
            if columns["presence"]
            else 0
        )

        distance_value = (
            to_number(last_row[columns["distance"]], 0)
            if columns["distance"]
            else 0
        )

        moving_value = (
            last_row[columns["moving"]]
            if columns["moving"] and pd.notna(last_row[columns["moving"]])
            else "N/D"
        )

        static_value = (
            last_row[columns["static"]]
            if columns["static"] and pd.notna(last_row[columns["static"]])
            else "N/D"
        )

        st.subheader("Ultimo Stato Rilevato")

        metric_presence, metric_distance, metric_moving, metric_static = st.columns(4)

        with metric_presence:
            st.metric(
                "Stato Rilevamento",
                "Presenza" if presence_value > 0 else "Assenza",
            )

        with metric_distance:
            st.metric(
                "Distanza Target",
                f"{distance_value:.0f} cm",
            )

        with metric_moving:
            st.metric(
                "Energia Moving",
                moving_value,
            )

        with metric_static:
            st.metric(
                "Energia Static",
                static_value,
            )

        st.markdown("### 🎯 Indicatore di Prossimità Radar")

        if presence_value <= 0 or distance_value <= 0:
            proximity = 0.0
            proximity_status = "⚪ Nessun target nel raggio d'azione"
        else:
            proximity = 1 - min(
                max(distance_value / MAX_RANGE_CM, 0.0),
                1.0,
            )

            if distance_value < 100:
                proximity_status = (
                    f"🔴 Rilevamento ravvicinato — {distance_value:.0f} cm"
                )
            elif distance_value < 300:
                proximity_status = (
                    f"🟠 Media distanza — {distance_value:.0f} cm"
                )
            else:
                proximity_status = (
                    f"🟢 Lunga distanza — {distance_value:.0f} cm"
                )

        st.progress(
            proximity,
            text=proximity_status,
        )

        st.divider()

        numeric_columns = [
            columns[key]
            for key in ["distance", "moving", "static"]
            if columns[key]
        ]

        df_chart = df.copy()

        for column in numeric_columns:
            df_chart[column] = pd.to_numeric(
                df_chart[column],
                errors="coerce",
            )

        if columns["presence"]:
            df_chart[columns["presence"]] = pd.to_numeric(
                df_chart[columns["presence"]],
                errors="coerce",
            )

        if samples != "Tutti":
            df_chart = df_chart.tail(int(samples))

        time_column = find_column(
            df,
            TIME_COLUMN_CANDIDATES,
        )

        if time_column:
            df_chart[time_column] = pd.to_datetime(
                df_chart[time_column],
                errors="coerce",
            )

            df_chart = df_chart.dropna(
                subset=[time_column]
            ).sort_values(time_column)

            if df_chart.empty:
                st.warning(
                    "La colonna temporale è presente, ma non contiene "
                    "date/orari validi. I grafici temporali non possono "
                    "essere generati."
                )
                return

            x_column = time_column
        else:
            df_chart = df_chart.reset_index(drop=True)
            df_chart["Campione"] = df_chart.index + 1
            x_column = "Campione"

        chart_columns = numeric_columns.copy()

        if columns["presence"]:
            chart_columns.append(columns["presence"])

        if chart_columns:
            st.subheader("📈 Analisi Dettagliata")

            left_column, right_column = st.columns(2)

            chart_specs = []

            if columns["distance"]:
                chart_specs.append(
                    (
                        left_column,
                        columns["distance"],
                        "📍 Distanza target (cm)",
                        "#00ffcc",
                    )
                )

            if columns["moving"]:
                chart_specs.append(
                    (
                        right_column,
                        columns["moving"],
                        "🚶 Energia Moving",
                        "#ff9900",
                    )
                )

            if columns["static"]:
                chart_specs.append(
                    (
                        left_column,
                        columns["static"],
                        "🧘 Energia Static",
                        "#ff00ff",
                    )
                )

            if columns["presence"]:
                chart_specs.append(
                    (
                        right_column,
                        columns["presence"],
                        "👁️ Stato rilevamento",
                        "#3399ff",
                    )
                )

            for container, y_column, title, color in chart_specs:
                figure = px.line(
                    df_chart,
                    x=x_column,
                    y=y_column,
                    title=title,
                    template="plotly_dark",
                )

                figure.update_traces(
                    line_color=color,
                    line_width=2,
                )

                figure.update_layout(
                    height=280,
                    margin=dict(
                        l=10,
                        r=10,
                        t=40,
                        b=10,
                    ),
                )

                container.plotly_chart(
                    figure,
                    use_container_width=True,
                )

        with st.expander(
            "🔍 Visualizza tabella dati grezzi (ultimi record)"
        ):
            st.dataframe(
                df.tail(50),
                use_container_width=True,
            )

    except Exception as error:
        st.error(
            f"Errore nel caricamento o elaborazione dei dati: {error}"
        )


radar_section()
