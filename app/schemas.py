from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(default="demo", min_length=1)
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class Source(BaseModel):
    file_name: str
    chunk_id: str
    score: float
    content_preview: str


class ChatResponse(BaseModel):
    session_id: str
    intent: str
    answer: str
    sources: list[Source] = []
    tool_result: dict[str, Any] | None = None
    model: str
    latency_ms: int


class KnowledgeImportRequest(BaseModel):
    path: str | None = None


class KnowledgeImportResponse(BaseModel):
    imported_files: int
    chunks: int
    vector_store: str
    files: list[str]


class SessionSummary(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class MessageRecord(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    intent: str | None
    created_at: str
