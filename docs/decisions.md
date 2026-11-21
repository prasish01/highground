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
| 2026-11-21 | Risk thresholds unchanged (SAFE_HEIGHT_M 10, SAFE_DISTANCE_M 500, weights 0.6/0.4, buffer 3 h) | Demo path and tests depend on them; no evidence yet to retune |
| 2026-11-21 | Gemini replies are validated; one retry, then template | Bad JSON or an invented fact must never reach a farmer |
| 2026-11-21 | Gemini reply rejected if it contains any number not in the facts | Simple, explainable guard against invented times, amounts, phone numbers |
| 2026-11-21 | Code's move + deadline always the first plan step | Safety-critical numbers come from code, never the model |
| 2026-11-21 | Live warnings cached 10 min; feed down → 200 with `live_status: "unavailable"` | Never a 500 on stage; UI must not read "unavailable" as "all clear" |
| 2026-11-21 | `river_rising` query param optional; when absent, the real gauge decides | Manual override still works for the demo; real data when present |
| 2026-11-21 | Live paddock elevations replace placeholders at startup; river elevation still the GeoJSON value | Open item: river elevation should come from the same DEM, or heights above river are wrong |
| 2026-11-21 | All farmer-facing times are New Zealand time (`ZoneInfo("Pacific/Auckland")`), whatever the server's time zone | A cloud server runs in UTC; "move by 4am" instead of "4pm" would be dangerous. The deadline is worked out in UTC then shown in NZ time so daylight saving can't shift the 3 h buffer |
| 2026-11-21 | API sends ready-made labels (`deadline_label`, `onset_label`, `expires_label`) | The UI never formats times itself, so browser time zones can't disagree with the message |
| 2026-11-21 | Bad elevation cache (missing, malformed, unknown ids, non-numeric) → log and keep GeoJSON value per paddock | Startup must never crash; the demo works offline |
