import json
import re
from dataclasses import dataclass

from app.services.keyword_service import match_keyword


@dataclass(frozen=True)
class IntentResult:
    intent: str
    command: str | None = None
    argument: str | None = None
    keyword: str | None = None
    keyword_reply: str | None = None


RAG_HINTS = (
    "知识库",
    "根据资料",
    "根据文档",
    "文档里",
    "资料里",
    "上面提到",
    "来源",
    "简历项目",
    # Legacy mojibake strings kept so old seeded tests/data still route.
    "鐭ヨ瘑搴",
    "鏍规嵁璧勬枡",
    "鏍规嵁鏂囨",
    "鏂囨。閲",
    "璧勬枡閲",
    "涓婇潰鎻愬埌",
    "鏉ユ簮",
    "绠€鍘嗛」鐩",
)

WEATHER_NOISE_PATTERN = re.compile(
    r"(查询|查一下|查查|查|帮我|帮忙|请|看看|看一下|看下|"
    r"天气|气温|温度|怎么样|怎样|如何|冷不冷|热不热|会不会下雨|会下雨吗|下雨吗|"
    r"weather|forecast|city)",
    re.IGNORECASE,
)

WEATHER_TIME_WORDS = ("现在", "当前", "今天", "明天", "后天")
FORECAST_RANGE_PATTERN = re.compile(r"未来\s*([0-9]+|[一二三四五六七八九十两]+)\s*(天|日|周|星期|礼拜)")


def detect_intent(message: str) -> IntentResult:
    text = message.strip()
    lowered = text.lower()

    keyword_hit = match_keyword(text)
    if keyword_hit:
        keyword, reply = keyword_hit
        return IntentResult(intent="keyword", keyword=keyword, keyword_reply=reply)

    if lowered.startswith("/time") or "现在几点" in text or "当前时间" in text or "北京时间" in text:
        argument = text.replace("/time", "", 1).strip() if lowered.startswith("/time") else _extract_time_location(text)
        return IntentResult(intent="tool", command="time", argument=argument)

    if any(hint in text for hint in RAG_HINTS):
        return IntentResult(intent="rag")

    weather_request = _parse_weather_request(text)
    if weather_request is not None:
        return IntentResult(
            intent="tool",
            command="weather",
            argument=json.dumps(weather_request, ensure_ascii=False),
        )

    if len(text) > 600:
        return IntentResult(intent="chat")

    return IntentResult(intent="chat")


def _extract_time_location(text: str) -> str | None:
    if "北京时间" in text:
        return "北京"
    match = re.search(r"([\u4e00-\u9fa5A-Za-z ]+)(?:现在几点|当前时间|时间)", text)
    if match:
        city = match.group(1)
        for prefix in ("查询", "查一下", "现在", "当前"):
            city = city.replace(prefix, "")
        return city.strip() or None
    return None


def _parse_weather_request(text: str) -> dict[str, object] | None:
    stripped = text.strip()
    lowered = stripped.lower()
    if lowered.startswith("/weather"):
        city = _clean_weather_city(stripped[len("/weather") :])
        return _weather_request(city or "北京")

    has_chinese_weather = "天气" in stripped or "气温" in stripped or "温度" in stripped
    has_english_weather = bool(re.search(r"\b(weather|forecast)\b", stripped, re.IGNORECASE))
    has_rain_query = "会不会下雨" in stripped or "会下雨吗" in stripped or "下雨吗" in stripped
    if not (has_chinese_weather or has_english_weather or has_rain_query):
        return None

    query_type = "current"
    day_offset = 0
    forecast_days = 1

    range_match = FORECAST_RANGE_PATTERN.search(stripped)
    if range_match:
        query_type = "daily_range"
        number = _parse_chinese_number(range_match.group(1))
        unit = range_match.group(2)
        forecast_days = number * 7 if unit in ("周", "星期", "礼拜") else number
    elif "明天" in stripped:
        query_type = "daily_one_day"
        day_offset = 1
    elif "后天" in stripped:
        query_type = "daily_one_day"
        day_offset = 2

    city_text = stripped
    if range_match:
        city_text = city_text[: range_match.start()] + city_text[range_match.end() :]
    for word in WEATHER_TIME_WORDS:
        city_text = city_text.replace(word, "")

    city = _clean_weather_city(city_text)
    return _weather_request(city or "北京", query_type, day_offset, forecast_days)


def _weather_request(
    city: str,
    query_type: str = "current",
    day_offset: int = 0,
    forecast_days: int = 1,
) -> dict[str, object]:
    return {
        "city": city,
        "query_type": query_type,
        "day_offset": day_offset,
        "forecast_days": forecast_days,
    }


def _clean_weather_city(value: str) -> str | None:
    text = value.strip()
    text = re.sub(r"^[,，:：\s]+|[,，?？!！.。\s]+$", "", text)
    text = WEATHER_NOISE_PATTERN.sub("", text)
    text = FORECAST_RANGE_PATTERN.sub("", text)
    for word in WEATHER_TIME_WORDS:
        text = text.replace(word, "")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[,，:：\s]+|[,，?？!！.。\s]+$", "", text)
    return text.strip() or None


def _parse_chinese_number(value: str) -> int:
    text = value.strip()
    if text.isdigit():
        return int(text)

    digits = {
        "零": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if text in digits:
        return digits[text]
    if text == "十":
        return 10
    if "十" in text:
        left, right = text.split("十", 1)
        tens = digits.get(left, 1) if left else 1
        ones = digits.get(right, 0) if right else 0
        return tens * 10 + ones
    return 1
