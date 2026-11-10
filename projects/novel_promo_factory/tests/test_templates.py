from app.templates import estimate_script_cost, generate_story_script


def test_generated_script_shape_and_budget():
    script = generate_story_script("测试故事", "悬疑", "她推开门。房间里没有人。桌上的信却刚刚写完。她回头时，电话响了。")
    shots = script["shots"]
    assert 6 <= len(shots) <= 10
    assert sum(1 for shot in shots if shot["kind"] == "seedance") <= 3
    estimate = estimate_script_cost(script)
    assert estimate["total_cny"] <= 20
    assert estimate["seedream_count"] >= 1
    assert estimate["seedance_count"] >= 1


def test_split_sentences_and_normalize():
    script = generate_story_script("短标题", "甜宠", "第一句。第二句！第三句？")
    assert len(script["hooks"]) == 3
    assert script["beats"][-1]["label"] == "CTA"
