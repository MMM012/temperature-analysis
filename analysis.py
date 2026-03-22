import time
import pandas as pd
import numpy as np
from multiprocessing import Pool, cpu_count


def load_data(path="temperature_data.csv"):
    """Загрузка данных + приведение timestamp к datetime."""
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


def compute_rolling(df, window=30):
    """Скользящее среднее и СКО по 30 дням по каждому городу."""
    df = df.sort_values(["city", "timestamp"]).copy()

    df["rolling_mean"] = (
        df.groupby("city")["temperature"]
        .transform(lambda x: x.rolling(window, min_periods=1).mean())
    )
    df["rolling_std"] = (
        df.groupby("city")["temperature"]
        .transform(lambda x: x.rolling(window, min_periods=1).std())
    )
    return df


def compute_season_stats(df):
    """Среднее и std по сезонам и городам."""
    stats = (
        df.groupby(["city", "season"])["temperature"]
        .agg(["mean", "std"])
        .reset_index()
    )
    return stats


def mark_anomalies(df, k=2.0):
    """
    Аномалии по формуле из задания:
    |T - rolling_mean| > 2 * rolling_std.
    """
    df = df.copy()
    df["is_anomaly"] = (df["temperature"] - df["rolling_mean"]).abs() > k * df["rolling_std"]
    return df


def analyze_city(city_df):
    """Анализ для одного города — отдельная функция для Pool."""
    city_df = compute_rolling(city_df)
    city_df = mark_anomalies(city_df)
    return city_df


def analyze_sequential(df):
    """Последовательный анализ для всех городов."""
    start = time.time()
    parts = []

    for city, city_df in df.groupby("city"):
        parts.append(analyze_city(city_df))

    result = pd.concat(parts, ignore_index=True)
    duration = time.time() - start
    return result, duration


def _analyze_city_wrapper(args):
    """Обёртка для multiprocessing.Pool."""
    city, city_df = args
    return analyze_city(city_df)


def analyze_parallel(df):
    """
    Параллельный анализ по городам с использованием multiprocessing.Pool.
    """
    start = time.time()
    grouped = list(df.groupby("city"))
    with Pool(processes=cpu_count()) as pool:
        parts = pool.map(_analyze_city_wrapper, grouped)

    result = pd.concat(parts, ignore_index=True)
    duration = time.time() - start
    return result, duration


if __name__ == "__main__":
    df = load_data()

    seq_res, t_seq = analyze_sequential(df)
    par_res, t_par = analyze_parallel(df)

    print(f"Sequential: {t_seq:.3f} s")
    print(f"Parallel:   {t_par:.3f} s")

