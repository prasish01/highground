"""Gemini plan: validation, retry and fallback. The Gemini call is always mocked."""

import json
import time

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


@pytest.fixture(autouse=True)
def empty_plan_cache(monkeypatch):
    monkeypatch.setattr(plan, "_plan_cache", {})


@pytest.fixture
def calls(monkeypatch):
    """Replace the Gemini call with a queue of canned replies; record each call."""
    made: list[str] = []
    replies: list = []

    def fake_generate(api_key, prompt, timeout_s):
        assert 0 < timeout_s <= plan.GEMINI_BUDGET_S
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


# --- issue #10: never stall the demo -----------------------------------------


def test_slow_gemini_times_out_to_the_template(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(plan, "GEMINI_BUDGET_S", 0.3)
    made = []

    def hangs(api_key, prompt, timeout_s):
        made.append(timeout_s)
        time.sleep(2)  # far longer than the budget
        return json.dumps(GOOD)

    monkeypatch.setattr(plan, "_generate", hangs)
    started = time.monotonic()
    result = make_plan(FACTS)
    assert time.monotonic() - started < 1.0
    assert result["source"] == "template"
    assert "timed out" in result["error"]
    assert len(made) == 1  # no retry once the time budget is used up


def test_retry_only_gets_the_time_that_is_left(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(plan, "GEMINI_BUDGET_S", 1.0)
    timeouts = []

    def slow_junk(api_key, prompt, timeout_s):
        timeouts.append(timeout_s)
        time.sleep(0.3)
        return "junk"

    monkeypatch.setattr(plan, "_generate", slow_junk)
    assert make_plan(FACTS)["source"] == "template"
    assert len(timeouts) == 2
    assert timeouts[1] < timeouts[0] <= 1.0


def test_same_facts_reuse_the_cached_gemini_plan(calls):
    made, replies = calls
    replies.append(json.dumps(GOOD))
    first = make_plan(FACTS)
    second = make_plan(dict(reversed(FACTS.items())))  # same facts, different key order
    assert first == second
    assert second["source"] == "gemini"
    assert len(made) == 1


def test_cached_plan_is_a_copy(calls):
    _, replies = calls
    replies.append(json.dumps(GOOD))
    make_plan(FACTS)["moves"].clear()
    assert make_plan(FACTS)["moves"] == GOOD["moves"]


def test_different_facts_call_gemini_again(calls):
    made, replies = calls
    replies.extend([json.dumps(GOOD), json.dumps(GOOD)])
    make_plan(FACTS)
    make_plan({**FACTS, "herd_size": 301})
    assert len(made) == 2


def test_failed_plan_is_cached_briefly_then_retried(calls, monkeypatch):
    made, replies = calls
    replies.extend(["junk", "junk"])
    assert make_plan(FACTS)["source"] == "template"
    assert make_plan(FACTS)["source"] == "template"
    assert len(made) == 2  # second press did not wait on Gemini again

    monkeypatch.setattr(plan, "FAILED_PLAN_TTL_S", -1)  # pretend the 2 minutes have passed
    replies.append(json.dumps(GOOD))
    assert make_plan(FACTS)["source"] == "gemini"
    assert len(made) == 3


def test_no_warning_uses_template_without_calling_gemini(calls):
    made, _ = calls
    result = make_plan({**FACTS, "warning": None, "recommendation": None})
    assert result["source"] == "template"
    assert made == []
