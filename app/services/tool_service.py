from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.config import get_settings


CITY_TIMEZONES = {
    "北京": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "广州": "Asia/Shanghai",
    "深圳": "Asia/Shanghai",
    "杭州": "Asia/Shanghai",
    "纽约": "America/New_York",
    "伦敦": "Europe/London",
    "东京": "Asia/Tokyo",
}

CITY_OFFSETS = {
    "Asia/Shanghai": 8,
    "America/New_York": -4,
    "Europe/London": 1,
    "Asia/Tokyo": 9,
}


def time_tool(location: str | None = None) -> dict[str, str]:
    city = (location or "北京").strip() or "北京"
    timezone = CITY_TIMEZONES.get(city, "Asia/Shanghai")
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        tz = timezone_from_offset(CITY_OFFSETS.get(timezone, 8))
    now = datetime.now(tz)
    return {
        "tool": "time",
        "location": city,
        "timezone": timezone,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def timezone_from_offset(hours: int) -> timezone:
    return timezone(timedelta(hours=hours))


async def weather_tool(city: str | None = None) -> dict[str, str]:
    settings = get_settings()
    city_name = (city or "北京").strip() or "北京"
    if not settings.weather_api_key:
        return {
            "tool": "weather",
            "city": city_name,
            "mode": "demo",
            "summary": f"{city_name}天气 Demo：多云，22-28 摄氏度，微风。配置 WEATHER_API_KEY 后可接入真实天气 API。",
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city_name, "appid": settings.weather_api_key, "units": "metric", "lang": "zh_cn"},
            )
            resp.raise_for_status()
            payload = resp.json()
        weather = payload.get("weather", [{}])[0].get("description", "未知")
        temp = payload.get("main", {}).get("temp", "未知")
        return {
            "tool": "weather",
            "city": city_name,
            "mode": "api",
            "summary": f"{city_name}当前天气：{weather}，温度 {temp} 摄氏度。",
        }
    except Exception as exc:
        return {
            "tool": "weather",
            "city": city_name,
            "mode": "fallback",
            "summary": f"天气 API 调用失败，已返回兜底结果：{city_name}今天适合关注实时天气预报。",
            "error": str(exc),
        }


async def run_tool(command: str, argument: str | None = None) -> dict[str, str]:
    if command == "time":
        return time_tool(argument)
    if command == "weather":
        return await weather_tool(argument)
    return {"tool": command, "error": "未知工具"}
