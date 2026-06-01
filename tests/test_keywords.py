from app.services.keyword_service import match_keyword


def test_match_keyword_reply():
    hit = match_keyword("请给我项目介绍")
    assert hit is not None
    keyword, reply = hit
    assert keyword == "项目介绍"
    assert "FastAPI" in reply
