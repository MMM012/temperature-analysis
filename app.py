import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from analysis import load_data, compute_rolling, compute_season_stats, mark_anomalies
from weather_api import get_current_temp_sync


# Заголовок
st.title("Анализ температурных данных")
st.write("Приложение для анализа исторических данных о температуре и мониторинга текущей погоды")

# Загрузка файла
uploaded_file = st.file_uploader("Загрузите CSV файл с историческими данными", type=["csv"])

if uploaded_file is not None:
    # Читаем данные
    df = pd.read_csv(uploaded_file, parse_dates=["timestamp"])
    st.success(f"Файл загружен! Всего записей: {len(df)}")
    
    # Обрабатываем
    df = compute_rolling(df)
    season_stats = compute_season_stats(df)
    df = mark_anomalies(df, season_stats)
    
    # Выбор города
    st.subheader("Выберите город для анализа")
    cities = sorted(df["city"].unique())
    selected_city = st.selectbox("Город:", cities)
    
    # Фильтруем
    city_df = df[df["city"] == selected_city].copy()
    
    # Статистика
    st.subheader(f"Статистика для города {selected_city}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего записей", len(city_df))
    with col2:
        st.metric("Найдено аномалий", city_df["is_anomaly"].sum())
    with col3:
        anomaly_percent = (city_df["is_anomaly"].sum() / len(city_df)) * 100
        st.metric("% аномалий", f"{anomaly_percent:.1f}%")
    
    # График
    st.subheader("График температуры с выделением аномалий")
    
    fig = go.Figure()
    
    normal_data = city_df[~city_df["is_anomaly"]]
    fig.add_trace(go.Scatter(
        x=normal_data["timestamp"],
        y=normal_data["temperature"],
        mode="markers",
        name="Нормальная температура",
        marker=dict(color="blue", size=3)
    ))
    
    anomaly_data = city_df[city_df["is_anomaly"]]
    fig.add_trace(go.Scatter(
        x=anomaly_data["timestamp"],
        y=anomaly_data["temperature"],
        mode="markers",
        name="Аномалия",
        marker=dict(color="red", size=5)
    ))
    
    fig.add_trace(go.Scatter(
        x=city_df["timestamp"],
        y=city_df["rolling_mean"],
        mode="lines",
        name="Скользящее среднее (30 дней)",
        line=dict(color="green", width=2)
    ))
    
    fig.update_layout(
        xaxis_title="Дата",
        yaxis_title="Температура (°C)",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Сезоны
    st.subheader("Статистика по сезонам")
    city_season_stats = season_stats[season_stats["city"] == selected_city]
    
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=city_season_stats["season"],
        y=city_season_stats["mean"],
        name="Средняя температура",
        error_y=dict(type="data", array=city_season_stats["std"])
    ))
    
    fig2.update_layout(
        xaxis_title="Сезон",
        yaxis_title="Температура (°C)"
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    st.write("Детальная статистика:")
    st.dataframe(city_season_stats)
    
    # Текущая погода
    st.subheader("Мониторинг текущей температуры")
    
    api_key = st.text_input("Введите API ключ OpenWeatherMap:", type="password")
    
    if api_key:
        st.info("Введите API ключ, чтобы получить текущую температуру")
    else:
        st.info("Введите API ключ, чтобы получить текущую температуру")
    
    if api_key:
        current_temp, error = get_current_temp_sync(selected_city, api_key)
        
        if error:
            st.error(f"Ошибка: {error}")
        else:
            st.success(f"Текущая температура в {selected_city}: **{current_temp}°C**")
            
            # Определяем сезон
            current_month = datetime.now().month
            if current_month in [12, 1, 2]:
                current_season = "winter"
            elif current_month in [3, 4, 5]:
                current_season = "spring"
            elif current_month in [6, 7, 8]:
                current_season = "summer"
            else:
                current_season = "autumn"
            
            season_data = city_season_stats[city_season_stats["season"] == current_season]
            
            if len(season_data) > 0:
                mean_temp = season_data["mean"].values[0]
                std_temp = season_data["std"].values[0]
                
                lower_bound = mean_temp - 2 * std_temp
                upper_bound = mean_temp + 2 * std_temp
                
                st.write(f"**Норма для сезона {current_season}:** {lower_bound:.1f}°C — {upper_bound:.1f}°C")
                
                is_anomaly = (current_temp < lower_bound) or (current_temp > upper_bound)
                
                if is_anomaly:
                    st.error("⚠️ Текущая температура АНОМАЛЬНАЯ для этого сезона!")
                else:
                    st.success("✅ Текущая температура в пределах нормы")
            else:
                st.warning("Нет данных для текущего сезона")
    
    # Инфо
    with st.expander("ℹ️ О методах получения данных"):
        st.write("""
        **Синхронный подход:**
        Запросы по очереди. Простой, но медленный при большом количестве городов.
        
        **Асинхронный подход:**
        Запросы параллельно. Быстрее для нескольких городов сразу.
        """)

else:
    st.info("👆 Загрузите CSV файл для начала анализа")
