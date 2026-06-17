import json

import pytest

from app.services.intent_service import detect_intent


def weather_argument(message: str) -> dict:
    result = detect_intent(message)
    assert result.intent == "tool"
    assert result.command == "weather"
    assert result.argument is not None
    return json.loads(result.argument)


def test_keyword_intent():
    result = detect_intent("你好，帮忙看一下")
    assert result.intent == "keyword"


def test_time_intent():
    result = detect_intent("北京时间")
    assert result.intent == "tool"
    assert result.command == "time"
    assert result.argument == "北京"


@pytest.mark.parametrize(
    ("message", "city"),
    [
        ("/weather 上海", "上海"),
        ("北京天气", "北京"),
        ("查询武汉天气", "武汉"),
        ("上海天气怎么样", "上海"),
        ("帮我看看东京天气", "东京"),
        ("查一下乌鲁木齐天气", "乌鲁木齐"),
        ("深圳现在天气怎么样", "深圳"),
        ("New York weather", "New York"),
        ("London weather", "London"),
        ("东京现在天气", "东京"),
    ],
)
def test_weather_intent_extracts_city(message: str, city: str):
    argument = weather_argument(message)
    assert argument["city"] == city
    assert argument["query_type"] == "current"


@pytest.mark.parametrize(
    ("message", "city", "query_type", "day_offset", "forecast_days"),
    [
        ("明天临沂天气", "临沂", "daily_one_day", 1, 1),
        ("后天武汉天气", "武汉", "daily_one_day", 2, 1),
        ("武汉未来一周天气", "武汉", "daily_range", 0, 7),
        ("未来十五天武汉天气", "武汉", "daily_range", 0, 15),
        ("武汉未来15天天气", "武汉", "daily_range", 0, 15),
        ("未来7天北京天气", "北京", "daily_range", 0, 7),
        ("查询未来一周上海天气", "上海", "daily_range", 0, 7),
        ("未来30天武汉天气", "武汉", "daily_range", 0, 30),
    ],
)
def test_weather_intent_extracts_forecast_range(
    message: str,
    city: str,
    query_type: str,
    day_offset: int,
    forecast_days: int,
):
    argument = weather_argument(message)
    assert argument["city"] == city
    assert argument["query_type"] == query_type
    assert argument["day_offset"] == day_offset
    assert argument["forecast_days"] == forecast_days


def test_chat_does_not_match_weather_without_weather_query():
    result = detect_intent("我们聊聊上海的旅游攻略")
    assert result.intent == "chat"


def test_rag_intent_keeps_priority():
    result = detect_intent("根据知识库介绍项目技术栈")
    assert result.intent == "rag"
