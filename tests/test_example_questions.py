from app import example_questions
from app.example_questions import HOME_EXAMPLE_COUNT, HOME_EXAMPLE_ORDER, HOME_EXAMPLE_POOLS, pick_home_examples


FORBIDDEN_HOME_CITIES = ("武汉", "北京", "上海", "广州", "深圳", "东京", "伦敦")
FORBIDDEN_HOME_TOPICS = (
    "天气",
    "下雨",
    "气温",
    "温度",
    "几点",
    "时间",
    "知识库",
    "资料",
    "文件",
    "账号",
    "路径",
)


def test_home_examples_pick_four_from_new_pools():
    examples = pick_home_examples()
    all_questions = {question for questions in HOME_EXAMPLE_POOLS.values() for question in questions}

    assert len(examples) == HOME_EXAMPLE_COUNT
    assert len({item["text"] for item in examples}) == HOME_EXAMPLE_COUNT
    assert set(HOME_EXAMPLE_ORDER) == {"fun", "development", "study"}
    assert all(item["text"] in HOME_EXAMPLE_POOLS[item["category"]] for item in examples)
    assert all(item["text"] in all_questions for item in examples)


def test_home_example_pool_has_no_forbidden_prompts():
    for questions in HOME_EXAMPLE_POOLS.values():
        for question in questions:
            assert not any(city in question for city in FORBIDDEN_HOME_CITIES)
            assert not any(topic in question for topic in FORBIDDEN_HOME_TOPICS)


def test_home_examples_avoid_repeating_same_group(monkeypatch):
    candidates = [
        {"category": category, "text": text}
        for category in HOME_EXAMPLE_ORDER
        for text in HOME_EXAMPLE_POOLS[category]
    ]
    repeated_group = candidates[:HOME_EXAMPLE_COUNT]
    previous_texts = frozenset(item["text"] for item in repeated_group)

    monkeypatch.setattr(example_questions, "_last_home_example_texts", previous_texts)
    monkeypatch.setattr(example_questions.random, "sample", lambda _items, _count: repeated_group.copy())

    examples = pick_home_examples()

    assert frozenset(item["text"] for item in examples) != previous_texts
