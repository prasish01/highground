# Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-11-21 | Name: HighGround | Says exactly what farmers do in a flood; instantly clear to judges |
| 2026-11-21 | Replay mode is the primary demo path | A real warning may not exist on demo day; the demo must always work |
| 2026-11-21 | Risk scoring in plain Python rules, not ML | Explainable to judges and farmers; testable |
| 2026-11-21 | Gemini only writes the plan from computed facts | Safety-critical numbers come from code; the model can't invent them |
| 2026-11-21 | Template plan fallback | Demo works without an API key or network |
| 2026-11-21 | Hawke's Bay as the demo region | Gabrielle context; HBRC river data is open (CC BY 4.0) |
| 2026-11-21 | Open Topo Data nzdem8m for elevation | Free, no key, fast enough for a hackathon; LINZ 1 m LiDAR as the upgrade |
| 2026-11-21 | FastAPI + React + Leaflet | Familiar stack; Vite proxy avoids CORS |
