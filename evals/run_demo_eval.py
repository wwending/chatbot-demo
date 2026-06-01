import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.ingest import import_knowledge
from app.schemas import ChatRequest
from app.services.chat_service import handle_chat


async def main() -> None:
    import_knowledge()
    questions = json.loads(Path("evals/questions.json").read_text(encoding="utf-8"))
    rows = []
    for index, item in enumerate(questions, start=1):
        started = time.perf_counter()
        response = await handle_chat(ChatRequest(user_id="eval", session_id="eval-session", message=item["question"]))
        latency_ms = int((time.perf_counter() - started) * 1000)
        ok = response.intent == item["expected_intent"]
        rows.append(
            {
                "index": index,
                "group": item["group"],
                "question": item["question"],
                "expected_intent": item["expected_intent"],
                "actual_intent": response.intent,
                "source_hit": bool(response.sources),
                "success": ok,
                "latency_ms": latency_ms,
                "note": "" if ok else "路由与预期不一致，需优化规则或阈值",
            }
        )
    Path("data/eval_result.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for row in rows if row["success"])
    print(f"Eval finished: {passed}/{len(rows)} passed. Result: data/eval_result.json")


if __name__ == "__main__":
    asyncio.run(main())
