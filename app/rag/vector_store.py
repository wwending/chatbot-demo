import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db.database import init_db, upsert_knowledge_source
from app.rag.embeddings import cosine_similarity, embed_text


@dataclass
class VectorRecord:
    chunk_id: str
    file_name: str
    file_path: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float]


@dataclass
class SearchResult:
    chunk_id: str
    file_name: str
    file_path: str
    content: str
    metadata: dict[str, Any]
    score: float


class LocalVectorStore:
    def __init__(self, path: Path | None = None) -> None:
        settings = get_settings()
        self.path = path or settings.vector_store_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: list[VectorRecord] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.records = []
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = [VectorRecord(**item) for item in data.get("records", [])]

    def persist(self) -> None:
        self.path.write_text(
            json.dumps({"records": [asdict(record) for record in self.records]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def upsert(self, records: list[VectorRecord]) -> None:
        by_id = {record.chunk_id: record for record in self.records}
        for record in records:
            by_id[record.chunk_id] = record
            upsert_knowledge_source(
                record.file_name,
                record.file_path,
                record.chunk_id,
                record.content,
                record.metadata,
            )
        self.records = list(by_id.values())
        self.persist()

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        query_embedding = embed_text(query)
        scored = [
            SearchResult(
                chunk_id=record.chunk_id,
                file_name=record.file_name,
                file_path=record.file_path,
                content=record.content,
                metadata=record.metadata,
                score=cosine_similarity(query_embedding, record.embedding),
            )
            for record in self.records
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def ready(self) -> bool:
        return self.path.exists()


def vector_store_ready() -> bool:
    try:
        init_db()
        return LocalVectorStore().ready()
    except Exception:
        return False
