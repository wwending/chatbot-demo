from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import db_ready, init_db, list_messages, list_sessions
from app.rag.ingest import import_knowledge
from app.rag.vector_store import LocalVectorStore, vector_store_ready
from app.schemas import (
    ChatRequest,
    ChatResponse,
    KnowledgeImportRequest,
    KnowledgeImportResponse,
    MessageRecord,
    SessionSummary,
)
from app.services.chat_service import handle_chat

app = FastAPI(title="Personal Knowledge Chatbot Demo", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    settings = get_settings()
    settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_store_path.parent.mkdir(parents=True, exist_ok=True)
    LocalVectorStore()


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "api": "ok",
        "sqlite": db_ready(),
        "vector_store": vector_store_ready(),
        "llm_configured": bool(settings.llm_api_key),
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model if settings.llm_api_key else "offline-demo",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await handle_chat(request)


@app.post("/knowledge/import", response_model=KnowledgeImportResponse)
async def knowledge_import(request: KnowledgeImportRequest | None = None) -> KnowledgeImportResponse:
    result = import_knowledge(request.path if request else None)
    return KnowledgeImportResponse(**result)


@app.post("/knowledge/upload", response_model=KnowledgeImportResponse)
async def knowledge_upload(file: UploadFile) -> KnowledgeImportResponse:
    if not file.filename or Path(file.filename).suffix.lower() not in {".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Only .txt and .md files are supported in this demo.")
    settings = get_settings()
    target = settings.knowledge_dir / Path(file.filename).name
    target.write_bytes(await file.read())
    result = import_knowledge(target)
    return KnowledgeImportResponse(**result)


@app.get("/sessions", response_model=list[SessionSummary])
def sessions(user_id: str | None = None) -> list[SessionSummary]:
    return [SessionSummary(**row) for row in list_sessions(user_id)]


@app.get("/sessions/{session_id}/messages", response_model=list[MessageRecord])
def messages(session_id: str) -> list[MessageRecord]:
    return [MessageRecord(**row) for row in list_messages(session_id)]
