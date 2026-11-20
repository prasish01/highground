"""Turn risk scores and a warning into a farm storm plan.

Uses Gemini when GEMINI_API_KEY is set; otherwise a deterministic template, so the demo
always works offline. The model only rewrites facts it is given — it must not add data.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .cap import Warning
from .risk import PaddockRisk, Recommendation, format_time

SYSTEM_PROMPT = """You write short, practical storm plans for New Zealand farmers.
Use ONLY the facts provided. Do not invent rainfall amounts, times, places or contacts.
Plain English, calm tone, specific to this farm. Official MetService warnings and
Civil Defence advice always come first.
Return JSON: {"summary": str, "moves": [{"time": str, "action": str}], "checklist": [str]}.
Keep the checklist to at most 8 items."""


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


def make_plan(f: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {**template_plan(f), "source": "template"}
    try:
        from google import genai  # imported lazily so tests don't need it

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=f"{SYSTEM_PROMPT}\n\nFACTS:\n{json.dumps(f)}",
            config={"response_mime_type": "application/json"},
        )
        return {**json.loads(response.text), "source": "gemini"}
    except Exception as exc:  # demo must never break on stage
        return {**template_plan(f), "source": "template", "error": str(exc)}
