import time
import requests
import aiohttp
import asyncio


def get_current_temp_sync(city, api_key):
    """Синхронно получить текущую температуру города."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}

    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        if resp.status_code != 200:
            err = data.get("message", "Unknown error")
            return None, f"Ошибка {resp.status_code}: {err}"

        temp = data["main"]["temp"]
        return temp, None
    except Exception as e:
        return None, f"Ошибка: {str(e)}"


async def _fetch_one_city(session, city, api_key):
    """Асинхронный запрос температуры для одного города."""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}

    try:
        async with session.get(url, params=params, timeout=10) as resp:
            data = await resp.json()
            if resp.status != 200:
                return {"city": city, "temp": None, "error": data.get("message")}
            return {"city": city, "temp": data["main"]["temp"], "error": None}
    except Exception as e:
        return {"city": city, "temp": None, "error": str(e)}


async def get_current_temp_async(cities, api_key):
    """Асинхронно получить температуру для списка городов."""
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_one_city(session, c, api_key) for c in cities]
        results = await asyncio.gather(*tasks)
        return results


def experiment_sync_async(cities, api_key):
    """
    Небольшой эксперимент: сравниваем время для sync и async.
    """
    # Синхронно
    start_sync = time.time()
    sync_results = []
    for c in cities:
        t, e = get_current_temp_sync(c, api_key)
        sync_results.append({"city": c, "temp": t, "error": e})
    dur_sync = time.time() - start_sync

    # Асинхронно
    start_async = time.time()
    async_results = asyncio.run(get_current_temp_async(cities, api_key))
    dur_async = time.time() - start_async

    return (sync_results, dur_sync), (async_results, dur_async)


if __name__ == "__main__":

    api_key = "___"
    cities = ["Berlin", "Cairo", "Dubai", "Beijing", "Moscow"]

    (sync_res, t_sync), (async_res, t_async) = experiment_sync_async(cities, api_key)

    print("Синхронно:", t_sync, "сек")
    print("Асинхронно:", t_async, "сек")

