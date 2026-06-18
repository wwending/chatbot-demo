import json
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx


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
    # Legacy mojibake aliases kept for old tests/data.
    "鍖椾含": "Asia/Shanghai",
    "鍖椾含鏃堕棿": "Asia/Shanghai",
    "涓婃捣": "Asia/Shanghai",
}

CITY_OFFSETS = {
    "Asia/Shanghai": 8,
    "America/New_York": -4,
    "Europe/London": 1,
    "Asia/Tokyo": 9,
}

WEATHER_CODE_DESCRIPTIONS = {
    0: "晴朗",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴天",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴强冰雹",
}

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


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


MAX_FORECAST_DAYS = 16


async def weather_tool(city: str | dict[str, Any] | None = None) -> dict[str, Any]:
    request = _parse_weather_argument(city)
    city_name = _clean_city(str(request.get("city") or ""), default="北京")
    query_type = str(request.get("query_type") or "current")
    day_offset = _safe_int(request.get("day_offset"), 0)
    forecast_days = _safe_int(request.get("forecast_days"), 1)

    if query_type == "daily_range" and forecast_days > MAX_FORECAST_DAYS:
        return {
            "tool": "weather",
            "city": city_name,
            "mode": "limit",
            "summary": f"当前最多支持未来 {MAX_FORECAST_DAYS} 天天气预报，请缩短查询范围后再试。",
            "error": "weather_forecast_days_exceeded",
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            location = await _resolve_location(client, city_name)
            if location is None:
                return {
                    "tool": "weather",
                    "city": city_name,
                    "mode": "not_found",
                    "summary": f"没有找到“{city_name}”的天气位置，请换一个更明确的城市名称再试。",
                    "error": "weather_city_not_found",
                }

            if query_type == "daily_one_day":
                daily = await _fetch_daily_weather(client, location, min(MAX_FORECAST_DAYS, day_offset + 1))
            elif query_type == "daily_range":
                daily = await _fetch_daily_weather(client, location, forecast_days)
            else:
                weather = await _fetch_current_weather(client, location)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        return _weather_error(city_name, f"weather_api_http_error:{status_code}")
    except httpx.RequestError:
        return _weather_error(city_name, "weather_api_request_error")
    except Exception:
        return _weather_error(city_name, "weather_api_unknown_error")

    resolved_location = _format_location(location)
    if query_type == "daily_one_day":
        return _format_one_day_forecast(city_name, resolved_location, daily, day_offset)
    if query_type == "daily_range":
        return _format_daily_range_forecast(city_name, resolved_location, daily, forecast_days)

    description = WEATHER_CODE_DESCRIPTIONS.get(_as_int(weather.get("weather_code")), "未知天气")
    temp = _format_number(weather.get("temperature_2m"))
    feels_like = _format_number(weather.get("apparent_temperature"))
    humidity = _format_number(weather.get("relative_humidity_2m"))
    wind_speed = _format_number(weather.get("wind_speed_10m"))
    return {
        "tool": "weather",
        "city": city_name,
        "resolved_location": resolved_location,
        "mode": "api",
        "summary": (
            f"{resolved_location}当前天气：{description}，温度 {temp}℃，"
            f"体感 {feels_like}℃，湿度 {humidity}%，风速 {wind_speed} km/h。"
        ),
    }


async def _resolve_location(client: httpx.AsyncClient, city_name: str) -> dict[str, Any] | None:
    response = await client.get(
        GEOCODING_URL,
        params={"name": city_name, "count": 1, "language": "zh", "format": "json"},
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results") or []
    if not results:
        return None
    return results[0]


async def _fetch_current_weather(client: httpx.AsyncClient, location: dict[str, Any]) -> dict[str, Any]:
    response = await client.get(
        FORECAST_URL,
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "timezone": location.get("timezone") or "auto",
        },
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("current") or {}


async def _fetch_daily_weather(
    client: httpx.AsyncClient,
    location: dict[str, Any],
    forecast_days: int,
) -> dict[str, Any]:
    response = await client.get(
        FORECAST_URL,
        params={
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
            ),
            "timezone": location.get("timezone") or "auto",
            "forecast_days": forecast_days,
        },
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("daily") or {}


async def run_tool(command: str, argument: str | None = None) -> dict[str, Any]:
    if command == "time":
        return time_tool(argument)
    if command == "weather":
        return await weather_tool(argument)
    return {"tool": command, "error": "unknown_tool"}


def _weather_error(city_name: str, error: str) -> dict[str, Any]:
    return {
        "tool": "weather",
        "city": city_name,
        "mode": "error",
        "summary": f"天气服务暂时不可用，暂时无法查询“{city_name}”的天气，请稍后再试。",
        "error": error,
    }


def _parse_weather_argument(argument: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(argument, dict):
        return argument
    if isinstance(argument, str):
        text = argument.strip()
        if text.startswith("{"):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                return {"city": text, "query_type": "current", "day_offset": 0, "forecast_days": 1}
            if isinstance(payload, dict):
                return payload
        return {"city": text, "query_type": "current", "day_offset": 0, "forecast_days": 1}
    return {"city": "北京", "query_type": "current", "day_offset": 0, "forecast_days": 1}


def _format_one_day_forecast(
    city_name: str,
    resolved_location: str,
    daily: dict[str, Any],
    day_offset: int,
) -> dict[str, Any]:
    label = "明天" if day_offset == 1 else "后天" if day_offset == 2 else "今天"
    item = _daily_item(daily, day_offset)
    description = WEATHER_CODE_DESCRIPTIONS.get(_as_int(item.get("weather_code")), "未知天气")
    high = _format_number(item.get("temperature_2m_max"))
    low = _format_number(item.get("temperature_2m_min"))
    probability = _format_number(item.get("precipitation_probability_max"))
    precipitation = _format_number(item.get("precipitation_sum"))
    wind_speed = _format_number(item.get("wind_speed_10m_max"))
    return {
        "tool": "weather",
        "city": city_name,
        "resolved_location": resolved_location,
        "mode": "daily_one_day",
        "summary": (
            f"{resolved_location}{label}天气：{description}，最高 {high}℃，最低 {low}℃，"
            f"降水概率 {probability}%，降水量 {precipitation} mm，最大风速 {wind_speed} km/h。"
        ),
    }


def _format_daily_range_forecast(
    city_name: str,
    resolved_location: str,
    daily: dict[str, Any],
    forecast_days: int,
) -> dict[str, Any]:
    lines = [f"{resolved_location}未来 {forecast_days} 天天气预报："]
    available_days = min(forecast_days, len(daily.get("time") or []))
    for index in range(available_days):
        item = _daily_item(daily, index)
        date = _format_daily_date(item.get("time"))
        description = WEATHER_CODE_DESCRIPTIONS.get(_as_int(item.get("weather_code")), "未知天气")
        low = _format_number(item.get("temperature_2m_min"))
        high = _format_number(item.get("temperature_2m_max"))
        probability = _format_number(item.get("precipitation_probability_max"))
        wind_speed = _format_number(item.get("wind_speed_10m_max"))
        lines.append(f"{date}：{description}，{low}-{high}℃，降水概率 {probability}%，最大风速 {wind_speed} km/h")
    return {
        "tool": "weather",
        "city": city_name,
        "resolved_location": resolved_location,
        "mode": "daily_range",
        "summary": "\n".join(lines),
    }


def _daily_item(daily: dict[str, Any], index: int) -> dict[str, Any]:
    item = {}
    for key, values in daily.items():
        if isinstance(values, list) and index < len(values):
            item[key] = values[index]
    return item


def _clean_city(value: str | None, default: str) -> str:
    text = (value or default).strip() or default
    for suffix in ("时间", "天气", "市", "鏃堕棿", "澶╂皵", "甯"):
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[: -len(suffix)]
    return text.strip() or default


def _format_daily_date(value: Any) -> str:
    if not isinstance(value, str):
        return "未知日期"
    try:
        return datetime.fromisoformat(value).strftime("%m-%d")
    except ValueError:
        return value


def _format_location(location: dict[str, Any]) -> str:
    parts = [
        location.get("name"),
        location.get("admin1"),
        location.get("country"),
    ]
    return "，".join(str(part) for part in parts if part)


def _format_number(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:g}"
    return "未知"


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
