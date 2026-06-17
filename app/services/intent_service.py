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
)


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

    if lowered.startswith("/weather") or "天气" in text:
        if lowered.startswith("/weather"):
            city = text.replace("/weather", "", 1).strip()
        else:
            city = _extract_city_from_weather(text)
        return IntentResult(intent="tool", command="weather", argument=city or "北京")

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


def _extract_city_from_weather(text: str) -> str | None:
    match = re.search(r"([\u4e00-\u9fa5A-Za-z]+)天气", text)
    if match:
        city = match.group(1)
        for prefix in ("查询", "查一下", "今天", "明天", "后天", "城市"):
            city = city.replace(prefix, "")
        return city.strip() or None
    return None
