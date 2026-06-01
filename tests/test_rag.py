from app.rag.ingest import import_knowledge
from app.rag.qa_service import search_knowledge


def test_import_and_search_knowledge():
    result = import_knowledge()
    assert result["imported_files"] >= 1
    assert result["chunks"] >= 1
    hits = search_knowledge("根据知识库介绍项目技术栈")
    assert hits
    assert hits[0].file_name.endswith(".md")
