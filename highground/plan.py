"""Turn risk scores and a warning into a farm storm plan.

Uses Gemini when GEMINI_API_KEY is set; otherwise a deterministic template, so the demo
always works offline. The model only rewrites facts it is given — it must not add data.
Every Gemini reply is checked (shape, length, no new numbers); a bad reply is retried once,
then we fall back to the template.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from .cap import Warning
from .risk import PaddockRisk, Recommendation, format_time

MAX_CHECKLIST = 8
MAX_MOVES = 8
GEMINI_ATTEMPTS = 2  # first try + one retry

SYSTEM_PROMPT = """You write short, practical storm plans for New Zealand farmers.

Rules (follow all of them):
- Use ONLY the facts in FACTS. Rewrite them in plain English; never add new facts.
- Do NOT add any number, time, date, rainfall amount, river level, place name, paddock name,
  phone number, website or contact that is not written in FACTS.
- Copy times and paddock names exactly as they appear in FACTS.
- If "recommendation" is given, the first move must state it exactly as written.
- If "warning" is null, say there is no active warning for this farm.
- If "warning.replay" is true, this is a replay of a past warning for practice.
- Calm, plain tone. Official MetService warnings and Civil Defence advice always come first.

Return ONLY JSON in exactly this shape:
{"summary": str, "moves": [{"time": str, "action": str}], "checklist": [str]}
At most 8 moves and at most 8 checklist items. Each checklist item is one short sentence."""


def facts(
    farm_name: str,
    herd_size: int,
    warning: Warning | None,
    risks: list[PaddockRisk],
    rec: Recommendation | None,
) -> dict[str, Any]:
    return {
        "farm": farm_name,
        "herd_size": herd_size,
        "warning": None
        if warning is None
        else {
            "event": warning.event,
            "level": warning.level,
            "onset": format_time(warning.onset),
            "expires": format_time(warning.expires),
            "replay": warning.is_replay,
        },
        "at_risk_paddocks": [r.name for r in risks if r.band == "red"],
        "watch_paddocks": [r.name for r in risks if r.band == "amber"],
        "recommendation": None if rec is None else rec.message,
    }


def template_plan(f: dict[str, Any]) -> dict[str, Any]:
    moves = []
    if f["recommendation"]:
        moves.append({"time": "Now", "action": f["recommendation"]})
    if f["at_risk_paddocks"]:
        moves.append(
            {
                "time": "Before onset",
                "action": "Keep stock out of " + ", ".join(f["at_risk_paddocks"]),
            }
        )
    w = f["warning"]
    summary = (
        f"{w['level'].title()} {w['event'].lower()} warning from {w['onset']}."
        if w
        else "No active warning for this farm."
    )
    return {
        "summary": summary,
        "moves": moves,
        "checklist": [
            "Consider bringing milking forward before the warning starts",
            "Fill generator fuel and test the generator",
            "Store drinking water for people and stock",
            "Move feed and machinery above flood-prone ground",
            "Charge phones and a battery radio",
            "Check on neighbours, especially anyone on their own",
            "Know your local Civil Defence contacts and evacuation routes",
        ],
    }


# --- checking Gemini's answer -------------------------------------------------

_NUMBER = re.compile(r"\d+")


def _is_text(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def validate_plan(raw: Any, f: dict[str, Any]) -> dict[str, Any] | None:
    """Return a clean plan if `raw` has the right shape and adds no numbers; else None.

    "No new numbers" is a simple, explainable guard: every digit group the model writes
    (times, amounts, phone numbers, paddock numbers) must already appear in the facts.
    """
    if not isinstance(raw, dict):
        return None
    summary, moves, checklist = raw.get("summary"), raw.get("moves"), raw.get("checklist")
    if not _is_text(summary) or not isinstance(moves, list) or not isinstance(checklist, list):
        return None
    if len(moves) > MAX_MOVES or len(checklist) > MAX_CHECKLIST:
        return None
    if not all(
        isinstance(m, dict) and _is_text(m.get("time")) and _is_text(m.get("action")) for m in moves
    ):
        return None
    if not all(_is_text(item) for item in checklist):
        return None

    clean_moves = [{"time": m["time"].strip(), "action": m["action"].strip()} for m in moves]
    clean = {
        "summary": summary.strip(),
        "moves": clean_moves,
        "checklist": [item.strip() for item in checklist],
    }

    allowed = set(_NUMBER.findall(json.dumps(f)))
    written = json.dumps(clean)
    if any(n not in allowed for n in _NUMBER.findall(written)):
        return None

    # The move and deadline come from code. If the model dropped them, put them back first.
    rec = f.get("recommendation")
    if rec and not any(rec in m["action"] for m in clean_moves):
        if len(clean_moves) >= MAX_MOVES:
            return None
        clean["moves"] = [{"time": "Now", "action": rec}, *clean_moves]
    return clean


def _generate(api_key: str, prompt: str) -> str:
    """One Gemini call. Kept separate so tests can replace it (no network in tests)."""
    from google import genai  # imported lazily so tests don't need it

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return response.text or ""


def make_plan(f: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {**template_plan(f), "source": "template"}

    prompt = f"{SYSTEM_PROMPT}\n\nFACTS:\n{json.dumps(f)}"
    error = "Gemini reply did not match the plan format"
    for _ in range(GEMINI_ATTEMPTS):
        try:
            plan = validate_plan(json.loads(_generate(api_key, prompt)), f)
        except Exception as exc:  # demo must never break on stage
            error = f"{type(exc).__name__}: {exc}"
            continue
        if plan is not None:
            return {**plan, "source": "gemini"}
    return {**template_plan(f), "source": "template", "error": error}
