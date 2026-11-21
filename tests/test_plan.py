"""Gemini plan: validation, retry and fallback. The Gemini call is always mocked."""

import json

import pytest

from highground import plan
from highground.plan import facts, make_plan, template_plan, validate_plan

FACTS = {
    "farm": "Demo Farm",
    "herd_size": 300,
    "warning": {
        "event": "Heavy Rain",
        "level": "red",
        "onset": "7pm",
        "expires": "1pm",
        "replay": True,
    },
    "at_risk_paddocks": ["Paddock 1", "Paddock 2"],
    "watch_paddocks": ["Paddock 4"],
    "recommendation": "Move the herd to Paddock 7 by 4pm",
}

GOOD = {
    "summary": "A red heavy rain warning starts at 7pm (replay).",
    "moves": [
        {"time": "Now", "action": "Move the herd to Paddock 7 by 4pm"},
        {"time": "Before 7pm", "action": "Keep stock out of Paddock 1 and Paddock 2"},
    ],
    "checklist": ["Fill generator fuel", "Store drinking water"],
}


@pytest.fixture
def calls(monkeypatch):
    """Replace the Gemini call with a queue of canned replies; record each call."""
    made: list[str] = []
    replies: list = []

    def fake_generate(api_key, prompt):
        made.append(prompt)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(plan, "_generate", fake_generate)
    return made, replies


def test_no_key_uses_template_without_calling_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def boom(*_):
        raise AssertionError("Gemini must not be called without a key")

    monkeypatch.setattr(plan, "_generate", boom)
    result = make_plan(FACTS)
    assert result["source"] == "template"
    assert result["moves"][0]["action"] == FACTS["recommendation"]


def test_good_gemini_reply_is_used(calls):
    made, replies = calls
    replies.append(json.dumps(GOOD))
    result = make_plan(FACTS)
    assert result["source"] == "gemini"
    assert result["moves"] == GOOD["moves"]
    assert len(made) == 1


def test_junk_twice_falls_back_to_template(calls):
    made, replies = calls
    replies.extend(["not json at all", json.dumps({"summary": 5})])
    result = make_plan(FACTS)
    assert result["source"] == "template"
    assert "error" in result
    assert len(made) == 2  # one retry, then give up


def test_junk_then_good_reply_retries_once(calls):
    made, replies = calls
    replies.extend(["{oops", json.dumps(GOOD)])
    assert make_plan(FACTS)["source"] == "gemini"
    assert len(made) == 2


def test_exception_falls_back_to_template(calls):
    _, replies = calls
    replies.extend([RuntimeError("network down"), RuntimeError("still down")])
    result = make_plan(FACTS)
    assert result["source"] == "template"
    assert result["moves"][0]["action"] == FACTS["recommendation"]
    assert "network down" in result["error"] or "still down" in result["error"]


def test_reply_with_invented_numbers_is_rejected(calls):
    made, replies = calls
    invented = {**GOOD, "summary": "Expect 250 mm of rain from 7pm."}
    replies.extend([json.dumps(invented), json.dumps(invented)])
    assert make_plan(FACTS)["source"] == "template"
    assert len(made) == 2


def test_validate_rejects_too_many_checklist_items():
    bad = {**GOOD, "checklist": [f"Item {i}" for i in range(1, 10)]}
    assert validate_plan(bad, FACTS) is None


def test_validate_rejects_bad_move_shape():
    assert validate_plan({**GOOD, "moves": ["Move now"]}, FACTS) is None
    assert validate_plan({**GOOD, "moves": [{"time": "Now"}]}, FACTS) is None
    assert validate_plan([GOOD], FACTS) is None


def test_validate_puts_the_code_recommendation_first_if_model_drops_it():
    reply = {**GOOD, "moves": [{"time": "Before 7pm", "action": "Keep stock off Paddock 1"}]}
    clean = validate_plan(reply, FACTS)
    assert clean is not None
    assert clean["moves"][0] == {"time": "Now", "action": FACTS["recommendation"]}


def test_prompt_contains_the_facts_and_the_no_new_facts_rule(calls):
    made, replies = calls
    replies.append(json.dumps(GOOD))
    make_plan(FACTS)
    assert "Do NOT add any number" in made[0]
    assert json.dumps(FACTS) in made[0]


def test_template_has_no_warning_summary_when_calm():
    f = facts("Demo Farm", 300, None, [], None)
    assert template_plan(f)["summary"] == "No active warning for this farm."
