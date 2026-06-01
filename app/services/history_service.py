from app.config import get_settings
from app.db.database import recent_messages


def load_history(session_id: str) -> list[dict[str, str]]:
    settings = get_settings()
    return recent_messages(session_id, limit=settings.history_turns * 2)
