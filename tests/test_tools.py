import asyncio

from app.services.tool_service import run_tool, time_tool


def test_time_tool():
    result = time_tool("北京")
    assert result["tool"] == "time"
    assert result["timezone"] == "Asia/Shanghai"
    assert "北京时间" in result["summary"]


def test_weather_tool_demo_mode():
    result = asyncio.run(run_tool("weather", "上海"))
    assert result["tool"] == "weather"
    assert "summary" in result
    assert "WEATHER_API_KEY" in result["summary"]
