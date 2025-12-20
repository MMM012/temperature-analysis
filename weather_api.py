import requests
import aiohttp
import asyncio


def get_current_temp_sync(city, api_key):
    """Получить текущую температуру для города синхронно"""
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        # если что-то пошло не так
        if resp.status_code != 200:
            err = data.get("message", "Неизвестная ошибка")
            return None, f"Ошибка {resp.status_code}: {err}"
        
        temp = data["main"]["temp"]
        return temp, None
        
    except Exception as e:
        return None, f"Ошибка: {str(e)}"


async def fetch_one_city(session, city, api_key):
    """Запрос для одного города асинхронно"""
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
    """Получить температуру для списка городов асинхронно"""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one_city(session, c, api_key) for c in cities]
        results = await asyncio.gather(*tasks)
        return results


# Синхронный метод проще, но медленный если надо запросить много городов подряд
# Асинхронный быстрее когда запрашиваешь сразу несколько городов, но код сложнее


if __name__ == "__main__":
    # тестируем
    key = "33d807253e84ec4f0f076145433eb5c1"
    
    print("Синхронно:")
    t, e = get_current_temp_sync("Moscow", key)
    if e:
        print(f"  Ошибка: {e}")
    else:
        print(f"  Москва: {t}°C")
    
    print("\nАсинхронно:")
    cities_list = ["Moscow", "Berlin", "Tokyo"]
    res = asyncio.run(get_current_temp_async(cities_list, key))
    for r in res:
        if r["error"]:
            print(f"  {r['city']}: ошибка - {r['error']}")
        else:
            print(f"  {r['city']}: {r['temp']}°C")
