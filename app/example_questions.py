import random
from typing import Final, Literal, TypedDict


ExampleCategory = Literal["weather", "time", "knowledge", "development"]


class ExampleQuestion(TypedDict):
    category: ExampleCategory
    text: str


HOME_EXAMPLE_POOLS: Final[dict[ExampleCategory, tuple[str, ...]]] = {
    "weather": (
        "今天天气适合跑步吗？",
        "今天出门会下雨吗？",
        "今天天气适合洗衣服吗？",
        "今天天气穿外套会热吗？",
        "今天天气适合户外活动吗？",
        "这几天天气适合运动吗？",
    ),
    "time": (
        "现在几点？",
        "当前时间是多少？",
        "现在几点了？",
        "当前时间？",
    ),
    "knowledge": (
        "根据知识库介绍项目",
        "根据知识库说明技术栈",
        "根据资料总结项目亮点",
        "知识库里项目如何工作？",
    ),
    "development": (
        "什么是指针？",
        "什么是头文件？",
        "什么是静态库和动态库？",
        "什么是 Makefile？",
        "什么是回调函数？",
        "什么是阻塞和非阻塞？",
        "什么是线程安全？",
        "什么是 TCP 三次握手？",
        "什么是端口？",
        "什么是 Linux 进程？",
        "什么是环境变量？",
        "什么是编译和链接？",
        "什么是内存泄漏？",
        "什么是栈和堆？",
        "什么是 const？",
        "什么是 unsigned int？",
    ),
}


HOME_EXAMPLE_ORDER: Final[tuple[ExampleCategory, ...]] = ("weather", "time", "knowledge", "development")


def pick_home_examples() -> list[ExampleQuestion]:
    """Pick one local example question from each home-page category."""
    return [
        {"category": category, "text": random.choice(HOME_EXAMPLE_POOLS[category])}
        for category in HOME_EXAMPLE_ORDER
    ]
