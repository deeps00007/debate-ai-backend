from services.debate_engine import build_debate_prompt, build_feedback_prompt


def test_beginner_prompt():
    messages = build_debate_prompt(
        topic="AI vs Human Jobs",
        difficulty="beginner",
        history=[{"role": "user", "content": "I think AI will create more jobs than it destroys"}],
    )
    assert len(messages) >= 2
    assert messages[0]["role"] == "system"
    assert "BEGINNER" in messages[0]["content"]
    assert "AI vs Human Jobs" in messages[0]["content"]
    assert messages[1]["role"] == "user"


def test_intermediate_prompt():
    messages = build_debate_prompt(
        topic="Online Education",
        difficulty="intermediate",
        history=[
            {"role": "user", "content": "Online education is more accessible"},
            {"role": "assistant", "content": "But what about practical skills?"},
        ],
    )
    assert len(messages) == 3
    assert messages[2]["role"] == "assistant"


def test_advanced_prompt():
    messages = build_debate_prompt(
        topic="Remote Work",
        difficulty="advanced",
        history=[],
    )
    assert "ADVANCED" in messages[0]["content"] or "aggressive" in messages[0]["content"].lower()


def test_feedback_prompt():
    prompt = build_feedback_prompt("User: I like AI\nAI: Interesting point", "AI Ethics")
    assert "communication_score" in prompt
    assert "persuasion_score" in prompt
    assert "logic_score" in prompt
    assert "tips" in prompt
