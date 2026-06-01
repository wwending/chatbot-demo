import json
import time

from app.config import get_settings
from app.db.database import add_message, ensure_session, save_keyword_hit, save_model_output
from app.rag.qa_service import answer_with_knowledge
from app.schemas import ChatRequest, ChatResponse, Source
from app.services.history_service import load_history
from app.services.intent_service import detect_intent
from app.services.llm_service import build_messages, call_llm
from app.services.tool_service import run_tool


async def handle_chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    started = time.perf_counter()
    session_id = ensure_session(request.user_id, request.session_id, request.message)
    user_message_id = add_message(session_id, "user", request.message)
    intent = detect_intent(request.message)
    history = load_history(session_id)

    sources: list[Source] = []
    tool_result = None
    model_name = settings.llm_model
    raw_response: object = {}
    prompt_tokens = 0
    completion_tokens = 0

    if intent.intent == "keyword":
        answer = intent.keyword_reply or ""
        if intent.keyword:
            save_keyword_hit(session_id, user_message_id, intent.keyword, answer)
        model_name = "keyword-rule"
        raw_response = {"keyword": intent.keyword}

    elif intent.intent == "tool":
        tool_result = await run_tool(intent.command or "", intent.argument)
        answer = tool_result.get("summary") or f"工具调用结果：{tool_result}"
        model_name = "tool-rule"
        raw_response = tool_result

    elif intent.intent == "rag" or _is_rag_follow_up(request.message, history):
        answer, rag_results, llm_result = await answer_with_knowledge(request.message, history)
        sources = [
            Source(
                file_name=item.file_name,
                chunk_id=item.chunk_id,
                score=round(item.score, 4),
                content_preview=item.content[:160],
            )
            for item in rag_results
        ]
        model_name = str(llm_result.get("model", model_name))
        raw_response = llm_result.get("raw", {})
        prompt_tokens = int(llm_result.get("prompt_tokens", 0))
        completion_tokens = int(llm_result.get("completion_tokens", 0))
        intent = type(intent)(intent="rag")

    else:
        system_prompt = "你是一个友好的通用文本聊天助手，回答简洁、清晰，并保持中文优先。"
        llm_result = await call_llm(build_messages(system_prompt, request.message, history), temperature=0.5)
        answer = llm_result["content"]
        model_name = str(llm_result.get("model", model_name))
        raw_response = llm_result.get("raw", {})
        prompt_tokens = int(llm_result.get("prompt_tokens", 0))
        completion_tokens = int(llm_result.get("completion_tokens", 0))

    latency_ms = int((time.perf_counter() - started) * 1000)
    assistant_message_id = add_message(session_id, "assistant", answer, intent.intent)
    save_model_output(
        session_id=session_id,
        message_id=assistant_message_id,
        model_name=model_name,
        raw_response=json.dumps(raw_response, ensure_ascii=False),
        final_answer=answer,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    return ChatResponse(
        session_id=session_id,
        intent=intent.intent,
        answer=answer,
        sources=sources,
        tool_result=tool_result,
        model=model_name,
        latency_ms=latency_ms,
    )


def _is_rag_follow_up(message: str, history: list[dict[str, str]]) -> bool:
    if not history:
        return False
    recent_had_rag = any(item.get("intent") == "rag" for item in history[-6:])
    if not recent_had_rag:
        return False
    follow_up_markers = ("它的", "它如何", "这个项目", "该项目", "上面提到", "如何保存", "技术栈有哪些")
    return any(marker in message for marker in follow_up_markers)
