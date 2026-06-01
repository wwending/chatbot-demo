import hashlib
from pathlib import Path

from app.config import get_settings
from app.db.database import init_db
from app.rag.embeddings import embed_text
from app.rag.loader import load_document, resolve_input_files
from app.rag.splitter import split_text
from app.rag.vector_store import LocalVectorStore, VectorRecord


def import_knowledge(path: str | Path | None = None) -> dict[str, object]:
    settings = get_settings()
    init_db()
    source_path = Path(path) if path else settings.knowledge_dir
    files = resolve_input_files(source_path)
    store = LocalVectorStore()
    records: list[VectorRecord] = []

    for file_path in files:
        text = load_document(file_path)
        chunks = split_text(text, settings.chunk_size, settings.chunk_overlap)
        for index, chunk in enumerate(chunks):
            digest = hashlib.sha1(f"{file_path.resolve()}:{index}:{chunk}".encode("utf-8")).hexdigest()[:16]
            chunk_id = f"{file_path.stem}-{index}-{digest}"
            metadata = {"chunk_index": index, "source_type": file_path.suffix.lower().lstrip(".")}
            records.append(
                VectorRecord(
                    chunk_id=chunk_id,
                    file_name=file_path.name,
                    file_path=str(file_path),
                    content=chunk,
                    metadata=metadata,
                    embedding=embed_text(chunk),
                )
            )

    store.upsert(records)
    return {
        "imported_files": len(files),
        "chunks": len(records),
        "vector_store": str(store.path),
        "files": [str(path) for path in files],
    }


if __name__ == "__main__":
    result = import_knowledge()
    print(result)
