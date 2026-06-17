from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.config import get_settings


CITY_TIMEZONES = {
    "北京": "Asia/Shanghai",
    "北京时间": "Asia/Shanghai",
    "上海": "Asia/Shanghai",
    "广州": "Asia/Shanghai",
    "深圳": "Asia/Shanghai",
    "杭州": "Asia/Shanghai",
    "纽约": "America/New_York",
    "伦敦": "Europe/London",
    "东京": "Asia/Tokyo",
    "Beijing": "Asia/Shanghai",
    "Shanghai": "Asia/Shanghai",
    "New York": "America/New_York",
    "London": "Europe/London",
    "Tokyo": "Asia/Tokyo",
}

CITY_OFFSETS = {
    "Asia/Shanghai": 8,
    "America/New_York": -4,
    "Europe/London": 1,
    "Asia/Tokyo": 9,
}

CITY_WEATHER_QUERY = {
    "北京": "Beijing,CN",
    "北京时间": "Beijing,CN",
    "上海": "Shanghai,CN",
    "广州": "Guangzhou,CN",
    "深圳": "Shenzhen,CN",
    "杭州": "Hangzhou,CN",
    "纽约": "New York,US",
    "伦敦": "London,GB",
    "东京": "Tokyo,JP",
}


def time_tool(location: str | None = None) -> dict[str, str]:
    city = _clean_city(location, default="北京")
    timezone_name = CITY_TIMEZONES.get(city, "Asia/Shanghai")
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = timezone_from_offset(CITY_OFFSETS.get(timezone_name, 8))
    now = datetime.now(tz)
    label = "北京时间" if timezone_name == "Asia/Shanghai" else f"{city}时间"
    return {
        "tool": "time",
        "location": city,
        "timezone": timezone_name,
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": f"{label}：{now.strftime('%Y-%m-%d %H:%M:%S')}",
    }


def timezone_from_offset(hours: int) -> timezone:
    return timezone(timedelta(hours=hours))


async def weather_tool(city: str | None = None) -> dict[str, str]:
    settings = get_settings()
    city_name = _clean_city(city, default="北京")
    if not settings.weather_api_key:
        return {
            "tool": "weather",
            "city": city_name,
            "mode": "demo",
            "summary": (
                f"{city_name}天气 Demo：多云，22-28 摄氏度，微风。"
                "如需真实天气，请在 .env 中配置 WEATHER_API_KEY=你的 OpenWeather API Key，"
                "然后重启客户端。"
            ),
        }

    try:
        query = CITY_WEATHER_QUERY.get(city_name, city_name)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": query, "appid": settings.weather_api_key, "units": "metric", "lang": "zh_cn"},
            )
            resp.raise_for_status()
            payload = resp.json()
        weather = payload.get("weather", [{}])[0].get("description", "未知")
        temp = payload.get("main", {}).get("temp", "未知")
        feels_like = payload.get("main", {}).get("feels_like", "未知")
        humidity = payload.get("main", {}).get("humidity", "未知")
        return {
            "tool": "weather",
            "city": city_name,
            "mode": "api",
            "summary": f"{city_name}当前天气：{weather}，温度 {temp} 摄氏度，体感 {feels_like} 摄氏度，湿度 {humidity}%。",
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


def _clean_city(value: str | None, default: str) -> str:
    text = (value or default).strip() or default
    for suffix in ("时间", "天气", "市"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    return text.strip() or default
