import asyncio
from typing import Any

import httpx

from app.config import get_settings


def build_messages(system_prompt: str, user_prompt: str, history: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    messages = [{"role": "system", "content": system_prompt}]
    for item in history or []:
        role = item.get("role")
        if role in {"user", "assistant"}:
            messages.append({"role": role, "content": item.get("content", "")})
    messages.append({"role": "user", "content": user_prompt})
    return messages


async def call_llm(messages: list[dict[str, str]], temperature: float = 0.3) -> dict[str, Any]:
    settings = get_settings()
    if not settings.llm_api_key:
        return _offline_response(messages)

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
    }

    last_error: Exception | None = None
    for attempt in range(settings.llm_max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            return {
                "content": content or "模型返回为空，请稍后重试。",
                "raw": data,
                "model": settings.llm_model,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.3 * (attempt + 1))

    return {
        "content": f"模型 API 调用失败，已进入兜底模式。错误：{last_error}",
        "raw": {"error": str(last_error)},
        "model": settings.llm_model,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


def _offline_response(messages: list[dict[str, str]]) -> dict[str, Any]:
    user_text = messages[-1]["content"] if messages else ""
    has_context = "检索片段" in user_text or "资料来源" in user_text
    if has_context:
        content = "离线 Demo 回答：我已根据检索到的知识片段生成回答。配置 LLM_API_KEY 后会由真实大模型结合来源生成更自然的答案。"
    else:
        content = "离线 Demo 回答：这是通用聊天兜底响应。配置 LLM_API_KEY 后可接入 DeepSeek 或通义千问。"
    return {
        "content": content,
        "raw": {"offline": True},
        "model": "offline-demo",
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }
