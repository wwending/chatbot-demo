KEYWORD_REPLIES: dict[str, str] = {
    "你好": "你好，我是个人知识问答机器人 Demo，可以聊天、查时间天气，也可以根据本地知识库回答问题。",
    "hello": "Hello! I can chat, answer from local knowledge, and call simple tools like time and weather.",
    "帮助": "你可以直接聊天，或输入 /time、/weather 北京，也可以问“根据知识库介绍项目技术栈”。",
    "项目介绍": "这是一个基于 FastAPI、SQLite、大模型 API 和 RAG 的个人知识问答聊天机器人原型。",
    "联系方式": "Demo 项目未绑定真实联系方式，可以在 README 中替换为你的邮箱、GitHub 或作品集地址。",
}


def match_keyword(message: str) -> tuple[str, str] | None:
    normalized = message.strip().lower()
    for keyword, reply in KEYWORD_REPLIES.items():
        if keyword.lower() in normalized:
            return keyword, reply
    return None
