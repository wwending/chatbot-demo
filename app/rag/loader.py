from pathlib import Path

from app.rag.cleaner import clean_text


SUPPORTED_EXTENSIONS = {".txt", ".md"}


def resolve_input_files(path: str | Path) -> list[Path]:
    root = Path(path)
    if root.is_file() and root.suffix.lower() in SUPPORTED_EXTENSIONS:
        return [root]
    if root.is_dir():
        return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)
    return []


def load_document(path: Path) -> str:
    return clean_text(path.read_text(encoding="utf-8"))
