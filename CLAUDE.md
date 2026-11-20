# CLAUDE.md — instructions for Claude Code

Read this first. Plan and timeline: `docs/plan.md`. Data sources: `docs/data-sources.md`.

## What HighGround is

A hackathon app (GDG, "Best Build for Aotearoa"). It turns NZ severe weather warnings into a
per-paddock plan: colours paddocks green/amber/red by flood risk, recommends where to move stock
and by when ("Move the herd to Paddock 7 by 4pm"), and writes a storm checklist with Gemini.

## The one thing that must always work

The demo path: load sample farm → press **Replay warning** → paddocks near the river turn red →
banner shows the move and deadline → **Show plan** shows the checklist. Never break this path.
Run `pytest` before every commit. Live data is a bonus, never a dependency of the demo.

## How to work with me (Prasish)

- I need to explain every line to judges. After each change, explain what and why, simply.
- One task at a time from `docs/plan.md`; stop at each checkpoint.
- Tests first for logic in `highground/` (geo, cap, risk, plan).
- Keep logic pure and dependency-free where possible; network code stays in `elevation.py`,
  `main.py` (live CAP) and `plan.py` (Gemini), each with a safe fallback.
- Commit small, with clear messages (`feat:`, `fix:`, `test:`, `docs:`).

## Hard rules

1. **Safety wording stays.** Every screen keeps: "Official MetService warnings and Civil Defence
   advice always come first. This is guidance, not a guarantee."
2. **No invented data.** Gemini only rewrites facts passed to it (see `SYSTEM_PROMPT` in
   `plan.py`). Never hard-code rainfall amounts, times or contacts as if they were real.
3. **Replay is labelled.** Anything from `data/replay_warning.xml` shows "REPLAY".
4. **Credit data** (MetService, LINZ via Open Topo Data, HBRC, OpenStreetMap) in README and an
   About screen.
5. **Secrets** live in `.env` only. Never commit keys.
6. **Te reo:** if we add any te reo, it is checked with a speaker and credited.

## Commands

```bash
source .venv/bin/activate
pytest
ruff check . && ruff format .
uvicorn highground.main:app --reload --env-file .env   # API on :8000, docs at /docs
cd web && npm run dev                                   # UI on :5173 (proxies /api to :8000)
```

## Architecture

- `highground/geo.py` — distances, centroids, areas, point-in-polygon (no dependencies)
- `highground/cap.py` — parse CAP 1.2 warnings; `as_replay()` shifts times to "now"
- `highground/risk.py` — `score_paddock()`, `recommend()`, thresholds at the top of the file
- `highground/farm.py` — load `data/sample_farm.geojson`
- `highground/elevation.py` — Open Topo Data nzdem8m lookups (max 100 points per call)
- `highground/plan.py` — Gemini plan with template fallback
- `highground/main.py` — FastAPI: `GET /api/farm`, `GET /api/assess?mode=calm|replay|live&river_rising=`
- `web/` — React + Leaflet; `src/App.tsx` is the whole UI for now

## Status

- [x] Core logic + 16 tests (geo, CAP, risk, recommendation, template plan)
- [x] FastAPI app and React UI written (run and check them first: untested in the scaffold)
- [ ] Replace sample replay warning with a real saved MetService CAP file
- [ ] Live elevation for paddocks (replace placeholder elevations)
- [ ] River gauge from HBRC Hilltop → `river_rising`
- [ ] Draw-your-own-paddocks
- [ ] Share by text / copy, About screen with credits
