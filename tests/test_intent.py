from app.services.intent_service import detect_intent


def test_keyword_intent():
    result = detect_intent("你好，帮助一下")
    assert result.intent == "keyword"


def test_time_intent():
    result = detect_intent("/time 纽约")
    assert result.intent == "tool"
    assert result.command == "time"


def test_weather_intent():
    result = detect_intent("上海天气怎么样")
    assert result.intent == "tool"
    assert result.command == "weather"
    assert result.argument == "上海"


def test_rag_intent():
    result = detect_intent("根据知识库介绍项目")
    assert result.intent == "rag"
