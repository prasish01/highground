# HighGround

**Know where your herd should be before the river rises.**

HighGround turns New Zealand severe weather warnings into a per-paddock plan. It checks official MetService warnings, paddock elevation and distance to the river, then colours each paddock green, amber or red, recommends where to move stock and by when, and writes a short storm checklist for farm staff.

> Built for the GDG hackathon — category: **Best Build for Aotearoa**.

> **Official MetService warnings and Civil Defence advice always come first. HighGround is guidance, not a guarantee.**

## Screenshots

![HighGround showing red paddocks by the river and the move banner]([TBD: docs/img/screenshot.png])

![Demo: Replay warning, paddocks turn red, Show plan]([TBD: docs/img/demo.gif])

*[TBD: add a screenshot and a short demo GIF of the replay path.]*

## The demo

1. Open the sample Hawke's Bay farm (fictional).
2. Press **Replay warning**: a sample heavy-rain warning in the official MetService alert format is applied (clearly labelled *Replay*). Live mode checks the real MetService feed.
3. Paddocks near the river turn red, and the banner says which paddock to move the herd to, and by when.
4. Press **Show plan** for the storm checklist, then print or share it.

## How it works

| Step | What happens |
|---|---|
| Warnings | MetService CAP feed (`alerts.metservice.com/cap/rss`), or a sample warning in replay mode |
| Land | Paddock height above the river and distance to the river (elevation via Open Topo Data / LINZ 8 m DEM) |
| Score | `0.6 × low ground + 0.4 × near river`, scaled by warning level (yellow 0.5, orange 0.8, red 1.0), +0.1 if the river is rising |
| Recommend | Lowest-risk paddock with water and room for the herd; deadline = warning onset − 3 hours |
| Plan | Gemini rewrites the facts into a short plan and checklist (template fallback if no API key) |

## Run it locally

Requires Python 3.12+ and Node 20+.

```bash
# Backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env                                  # add GEMINI_API_KEY (optional)
pytest                                                # 16 tests
uvicorn highground.main:app --reload --env-file .env  # http://localhost:8000/docs

# Frontend (second terminal)
cd web
npm install
npm run dev                                           # http://localhost:5173
```

## Project layout

```
highground/      Python package: geo, CAP parsing, risk scoring, plan, FastAPI app
data/            sample_farm.geojson (fictional farm), replay_warning.xml (SAMPLE, replace before demo)
web/             React + TypeScript + Vite frontend (map drawn in SVG)
tests/           pytest suite for the core logic
docs/            hackathon plan, data sources, decisions, pitch
```

## Data and credits

- Severe weather warnings: **MetService** (CAP feed).
- Elevation: **Toitū Te Whenua LINZ** elevation data (CC BY 4.0), served via **Open Topo Data** (nzdem8m).
- River levels (planned): **Hawke's Bay Regional Council** Hilltop open data (CC BY 4.0).
- Map tiles: © OpenStreetMap contributors.

The sample farm is **fictional**, and `data/replay_warning.xml` is a **sample** warning to be replaced with a real saved MetService CAP file before the demo. See [`docs/data-sources.md`](docs/data-sources.md).

## Built during the hackathon

Be upfront with judges about what came before the event and what was built on the day.

**Prepared before the event:** [TBD: e.g. idea, docs, data research, initial scaffold — confirm against the event rules]

**Built during the hackathon:**

- About screen with data credits and the safety statement (`web/src/components/About.tsx`)
- Share plan: copy as text and print (`web/src/components/SharePlan.tsx`)
- Timed pitch script, demo checklist and farmer interview guide (`docs/`)
- [TBD: add each feature as it is merged]

## How we worked

Four Claude teammates built HighGround in parallel, one role each (Map + UI, Data, Logic + AI, Story + polish), with one human integrator reviewing and merging. Each role worked on its own files and opened one pull request per role, so changes stayed small and easy to review.

## Our team

| Name | Role |
|---|---|
| [TBD] | Map + UI |
| [TBD] | Data |
| [TBD] | Logic + AI |
| [TBD] | Story + polish |

## Author

**Prasish Bhatta**, Auckland. Licence: [MIT](LICENSE).
