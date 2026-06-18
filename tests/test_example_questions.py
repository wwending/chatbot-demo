from app.example_questions import HOME_EXAMPLE_ORDER, HOME_EXAMPLE_POOLS, pick_home_examples


FORBIDDEN_HOME_CITIES = ("武汉", "北京", "上海", "广州", "深圳", "东京", "伦敦")


def test_home_examples_pick_one_per_category():
    examples = pick_home_examples()

    assert len(examples) == 4
    assert [item["category"] for item in examples] == list(HOME_EXAMPLE_ORDER)
    assert all(item["text"] in HOME_EXAMPLE_POOLS[item["category"]] for item in examples)


def test_home_example_pool_has_no_specific_city_names():
    for questions in HOME_EXAMPLE_POOLS.values():
        for question in questions:
            assert not any(city in question for city in FORBIDDEN_HOME_CITIES)
