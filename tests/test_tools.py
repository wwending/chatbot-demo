import asyncio
import json

import httpx

from app.services import tool_service
from app.services.tool_service import run_tool, time_tool


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test/redacted")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("status error", request=request, response=response)


class FakeAsyncClient:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, params: dict) -> FakeResponse:
        self.requests.append((url, params))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def patch_client(monkeypatch, responses: list[FakeResponse | Exception]) -> FakeAsyncClient:
    fake_client = FakeAsyncClient(responses)
    monkeypatch.setattr(tool_service.httpx, "AsyncClient", lambda timeout: fake_client)
    return fake_client


def weather_arg(city: str, query_type: str = "current", day_offset: int = 0, forecast_days: int = 1) -> str:
    return json.dumps(
        {
            "city": city,
            "query_type": query_type,
            "day_offset": day_offset,
            "forecast_days": forecast_days,
        },
        ensure_ascii=False,
    )


def location_payload(city: str = "武汉") -> dict:
    return {
        "results": [
            {
                "name": city,
                "latitude": 30.5872,
                "longitude": 114.3055,
                "timezone": "Asia/Shanghai",
                "country": "中国",
                "admin1": "湖北",
            }
        ]
    }


def daily_payload(days: int) -> dict:
    return {
        "daily": {
            "time": [f"2026-06-{17 + index:02d}" for index in range(days)],
            "weather_code": [3 for _ in range(days)],
            "temperature_2m_max": [31 for _ in range(days)],
            "temperature_2m_min": [24 for _ in range(days)],
            "apparent_temperature_max": [33 for _ in range(days)],
            "apparent_temperature_min": [25 for _ in range(days)],
            "precipitation_sum": [0.5 for _ in range(days)],
            "precipitation_probability_max": [30 for _ in range(days)],
            "wind_speed_10m_max": [9 for _ in range(days)],
        }
    }


def test_time_tool():
    result = time_tool("北京")
    assert result["tool"] == "time"
    assert result["timezone"] == "Asia/Shanghai"
    assert "北京时间" in result["summary"]


def test_weather_tool_open_meteo_success(monkeypatch):
    fake_client = patch_client(
        monkeypatch,
        [
            FakeResponse(location_payload()),
            FakeResponse(
                {
                    "current": {
                        "temperature_2m": 28,
                        "apparent_temperature": 30,
                        "relative_humidity_2m": 70,
                        "weather_code": 3,
                        "wind_speed_10m": 8,
                    }
                }
            ),
        ],
    )

    result = asyncio.run(run_tool("weather", "武汉"))

    assert result["tool"] == "weather"
    assert result["mode"] == "api"
    assert result["resolved_location"] == "武汉，湖北，中国"
    assert "阴天" in result["summary"]
    assert "温度 28℃" in result["summary"]
    assert fake_client.requests[0][0] == tool_service.GEOCODING_URL
    assert fake_client.requests[0][1]["name"] == "武汉"
    assert fake_client.requests[1][0] == tool_service.FORECAST_URL
    assert "current" in fake_client.requests[1][1]


def test_weather_tool_daily_one_day(monkeypatch):
    fake_client = patch_client(
        monkeypatch,
        [
            FakeResponse(location_payload("临沂")),
            FakeResponse(daily_payload(2)),
        ],
    )

    result = asyncio.run(run_tool("weather", weather_arg("临沂", "daily_one_day", day_offset=1)))

    assert result["tool"] == "weather"
    assert result["mode"] == "daily_one_day"
    assert "临沂，湖北，中国明天天气" in result["summary"]
    assert "最高 31℃" in result["summary"]
    assert "最低 24℃" in result["summary"]
    assert "降水概率 30%" in result["summary"]
    assert "降水量 0.5 mm" in result["summary"]
    assert fake_client.requests[0][1]["name"] == "临沂"
    assert fake_client.requests[1][1]["forecast_days"] == 2
    assert "daily" in fake_client.requests[1][1]


def test_weather_tool_daily_range_7_days(monkeypatch):
    fake_client = patch_client(
        monkeypatch,
        [
            FakeResponse(location_payload()),
            FakeResponse(daily_payload(7)),
        ],
    )

    result = asyncio.run(run_tool("weather", weather_arg("武汉", "daily_range", forecast_days=7)))

    assert result["mode"] == "daily_range"
    assert "武汉，湖北，中国未来 7 天天气预报" in result["summary"]
    assert result["summary"].count("降水概率") == 7
    assert "06-17：阴天，24-31℃" in result["summary"]
    assert fake_client.requests[0][1]["name"] == "武汉"
    assert fake_client.requests[1][1]["forecast_days"] == 7


def test_weather_tool_daily_range_15_days(monkeypatch):
    patch_client(
        monkeypatch,
        [
            FakeResponse(location_payload()),
            FakeResponse(daily_payload(15)),
        ],
    )

    result = asyncio.run(run_tool("weather", weather_arg("武汉", "daily_range", forecast_days=15)))

    assert result["mode"] == "daily_range"
    assert "未来 15 天天气预报" in result["summary"]
    assert result["summary"].count("降水概率") == 15


def test_weather_tool_rejects_more_than_16_days(monkeypatch):
    fake_client = patch_client(monkeypatch, [])

    result = asyncio.run(run_tool("weather", weather_arg("武汉", "daily_range", forecast_days=30)))

    assert result["mode"] == "limit"
    assert result["error"] == "weather_forecast_days_exceeded"
    assert "最多支持未来 16 天" in result["summary"]
    assert fake_client.requests == []


def test_weather_tool_city_not_found(monkeypatch):
    patch_client(monkeypatch, [FakeResponse({"results": []})])

    result = asyncio.run(run_tool("weather", "不存在城市"))

    assert result["tool"] == "weather"
    assert result["mode"] == "not_found"
    assert result["error"] == "weather_city_not_found"
    assert "没有找到" in result["summary"]


def test_weather_tool_request_error_is_safe(monkeypatch):
    request = httpx.Request("GET", "https://api.open-meteo.com/v1/forecast?secret=should-not-leak")
    patch_client(monkeypatch, [httpx.RequestError("boom https://secret.example", request=request)])

    result = asyncio.run(run_tool("weather", "上海"))

    assert result["tool"] == "weather"
    assert result["mode"] == "error"
    assert result["error"] == "weather_api_request_error"
    assert "secret" not in str(result)
    assert "https://" not in str(result)


def test_weather_tool_http_error_is_safe(monkeypatch):
    patch_client(monkeypatch, [FakeResponse({}, status_code=404)])

    result = asyncio.run(run_tool("weather", "上海"))

    assert result["error"] == "weather_api_http_error:404"
    assert "https://" not in str(result)
