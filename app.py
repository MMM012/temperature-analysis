import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from analysis import load_data, compute_rolling, compute_season_stats, mark_anomalies
from weather_api import get_current_temp_sync


st.title("Анализ температур и текущей погоды")
st.write(
    "Загрузка исторических данных, поиск аномалий и мониторинг текущей температуры "
    "через OpenWeatherMap."
)


# Загрузка CSV с историческими данными
uploaded_file = st.file_uploader(
    "Загрузите файл temperature_data.csv", type=["csv"]
)

# Форма для ввода API-ключа
with st.form("api_form"):
    api_key = st.text_input(
        "Введите API-ключ OpenWeatherMap",
        type="password",
        help="При пустом ключе запрос текущей погоды выполняться не будет.",
    )
    submitted = st.form_submit_button("Сохранить ключ")

if uploaded_file is not None:
    # Чтение данных
    df = pd.read_csv(uploaded_file, parse_dates=["timestamp"])

    st.success(f"Файл загружен. Всего записей: {len(df)}")

    # Аналитика
    df = compute_rolling(df)
    season_stats = compute_season_stats(df)
    df = mark_anomalies(df)

    # Выбор города
    st.subheader("Выбор города")
    cities = sorted(df["city"].unique())
    selected_city = st.selectbox("Город", cities)

    city_df = df[df["city"] == selected_city].copy()
    city_season_stats = season_stats[season_stats["city"] == selected_city]

    # Описательная статистика
    st.subheader(f"Описательная статистика для {selected_city}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Количество записей", len(city_df))
    with col2:
        anomalies_count = int(city_df["is_anomaly"].sum())
        st.metric("Аномалий", anomalies_count)
    with col3:
        anomaly_percent = city_df["is_anomaly"].mean() * 100 if len(city_df) > 0 else 0.0
        st.metric("% аномалий", f"{anomaly_percent:.1f}%")

    st.write("Базовая статистика по температуре:")
    st.dataframe(
        city_df["temperature"].describe().to_frame().T
    )

    # Временной ряд с аномалиями
    st.subheader("Временной ряд температур с выделением аномалий")

    fig = go.Figure()

    normal_data = city_df[~city_df["is_anomaly"]]
    fig.add_trace(
        go.Scatter(
            x=normal_data["timestamp"],
            y=normal_data["temperature"],
            mode="markers",
            name="Нормальная температура",
            marker=dict(color="blue", size=3),
        )
    )

    anomaly_data = city_df[city_df["is_anomaly"]]
    fig.add_trace(
        go.Scatter(
            x=anomaly_data["timestamp"],
            y=anomaly_data["temperature"],
            mode="markers",
            name="Аномалии",
            marker=dict(color="red", size=5),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=city_df["timestamp"],
            y=city_df["rolling_mean"],
            mode="lines",
            name="Скользящее среднее (30 дней)",
            line=dict(color="green", width=2),
        )
    )

    fig.update_layout(
        xaxis_title="Дата",
        yaxis_title="Температура (°C)",
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Сезонные профили
    st.subheader("Сезонные профили")

    fig2 = go.Figure()
    fig2.add_trace(
        go.Bar(
            x=city_season_stats["season"],
            y=city_season_stats["mean"],
            name="Средняя температура",
            error_y=dict(type="data", array=city_season_stats["std"]),
        )
    )
    fig2.update_layout(
        xaxis_title="Сезон",
        yaxis_title="Температура (°C)",
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.write("Таблица сезонной статистики:")
    st.dataframe(city_season_stats)

    # Текущая температура и проверка на аномальность
    st.subheader("Текущая температура и её аномальность")

    if not api_key:
        st.info("API-ключ не указан. Введите ключ, чтобы получить текущую погоду.")
    else:
        current_temp, error = get_current_temp_sync(selected_city, api_key)

        if error:
            st.error(f"Ошибка при запросе: {error}")
        else:
            st.success(f"Текущая температура в {selected_city}: {current_temp}°C")

            # Определяем текущий сезон (схема совпадает с генерацией данных)
            month = datetime.now().month
            if month in [12, 1, 2]:
                current_season = "winter"
            elif month in [3, 4, 5]:
                current_season = "spring"
            elif month in [6, 7, 8]:
                current_season = "summer"
            else:
                current_season = "autumn"

            st.write(f"Текущий сезон: **{current_season}**")

            season_row = city_season_stats[
                city_season_stats["season"] == current_season
            ]

            if len(season_row) == 0:
                st.warning("Нет исторических данных для текущего сезона.")
            else:
                mean_temp = season_row["mean"].values[0]
                std_temp = season_row["std"].values[0]

                lower = mean_temp - 2 * std_temp
                upper = mean_temp + 2 * std_temp

                st.write(
                    f"Нормальный диапазон для сезона: "
                    f"{lower:.1f}°C — {upper:.1f}°C"
                )

                is_anomaly = (current_temp < lower) or (current_temp > upper)

                if is_anomaly:
                    st.error("Текущая температура АНОМАЛЬНАЯ для этого сезона.")
                else:
                    st.success("Текущая температура в пределах сезонной нормы.")

    with st.expander("О способах получения текущей температуры"):
        st.write(
            """
            **Синхронный способ** делает запросы последовательно — код проще,
            но при большом количестве городов запросы занимают больше времени.

            **Асинхронный способ** позволяет отправлять несколько запросов параллельно.
            В отдельном модуле `weather_api.py` проведён небольшой эксперимент
            по измерению времени для обоих подходов.
            """
        )

else:
    st.info("Загрузите файл с историческими данными, чтобы начать анализ.")
