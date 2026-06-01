from app.config import get_settings
from app.rag.vector_store import LocalVectorStore, SearchResult
from app.services.llm_service import build_messages, call_llm


def search_knowledge(query: str) -> list[SearchResult]:
    settings = get_settings()
    results = LocalVectorStore().search(query, top_k=settings.rag_top_k)
    return [item for item in results if item.score >= settings.rag_min_score]


async def answer_with_knowledge(query: str, history: list[dict[str, str]]) -> tuple[str, list[SearchResult], dict[str, object]]:
    results = search_knowledge(query)
    if not results:
        return "知识库中没有检索到足够相关的资料。你可以先调用 /knowledge/import 导入文档。", [], {
            "raw": {"no_sources": True},
            "model": "rag-router",
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    context = "\n\n".join(
        f"[资料来源: {item.file_name} | chunk: {item.chunk_id} | score: {item.score:.3f}]\n{item.content}"
        for item in results
    )
    system_prompt = (
        "你是一个严谨的个人知识库问答助手。只能基于检索片段回答；"
        "如果资料不足，请明确说明。回答末尾用“来源：文件名”列出依据。"
    )
    user_prompt = f"检索片段：\n{context}\n\n用户问题：{query}"
    llm_result = await call_llm(build_messages(system_prompt, user_prompt, history), temperature=0.2)
    return llm_result["content"], results, llm_result
