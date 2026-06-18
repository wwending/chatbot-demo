import random
from typing import Final, Literal, TypedDict


ExampleCategory = Literal["fun", "development", "study"]


class ExampleQuestion(TypedDict):
    category: ExampleCategory
    text: str


HOME_EXAMPLE_POOLS: Final[dict[ExampleCategory, tuple[str, ...]]] = {
    "fun": (
        "给我来个冷笑话",
        "讲个程序员笑话",
        "出一道脑筋急转弯",
        "给我一个摸鱼小知识",
        "给我一句适合今天的鼓励",
        "讲一个和学习有关的小段子",
    ),
    "development": (
        "什么是线程安全？",
        "进程和线程有什么区别？",
        "解释一下什么是 API",
        "什么是 JSON？",
        "什么是 Git commit？",
        "C++ 指针和引用有什么区别？",
        "什么是内存泄漏？",
        "什么是 Linux 进程？",
    ),
    "study": (
        "给我一个今天的学习建议",
        "如何高效阅读英文技术文档？",
        "如何避免学习时分心？",
        "怎么复习 C++ 基础？",
    ),
}


HOME_EXAMPLE_COUNT: Final[int] = 4
HOME_EXAMPLE_ORDER: Final[tuple[ExampleCategory, ...]] = ("fun", "development", "study")

_last_home_example_texts: frozenset[str] | None = None


def pick_home_examples() -> list[ExampleQuestion]:
    """Pick four local example questions for the welcome page."""
    global _last_home_example_texts

    candidates = [
        {"category": category, "text": text}
        for category in HOME_EXAMPLE_ORDER
        for text in HOME_EXAMPLE_POOLS[category]
    ]
    examples = random.sample(candidates, HOME_EXAMPLE_COUNT)
    current_texts = frozenset(item["text"] for item in examples)

    if _last_home_example_texts is not None and current_texts == _last_home_example_texts:
        used_texts = set(current_texts)
        for index, _item in enumerate(examples):
            replacement = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate["text"] not in _last_home_example_texts
                    and candidate["text"] not in used_texts
                ),
                None,
            )
            if replacement is not None:
                used_texts.remove(examples[index]["text"])
                examples[index] = replacement
                used_texts.add(replacement["text"])
                break

    _last_home_example_texts = frozenset(item["text"] for item in examples)
    return examples
