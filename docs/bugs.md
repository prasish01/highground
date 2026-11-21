# Bugs

Owner: Teammate 5 (QA). Every bug found in integration runs. P1 and P2 bugs each have a GitHub issue.

**Severity:** P1 = breaks the demo path · P2 = visible or breaks a hard rule · P3 = minor or polish

**Owners:** T1 UI (`App.tsx`, `styles.css`, `api.ts`) · T2 Data (`data/`, `cap.py`, `elevation.py`, `river.py`) · T3 Logic (`risk.py`, `plan.py`, `main.py`, `farm.py`) · T4 Story (`About.tsx`, `SharePlan.tsx`, pitch, README) · Prasish (repo settings)

Last updated: 2026-11-21 14:00 NZDT

| ID | Sev | Area | Owner | Steps to reproduce | Status |
|---|---|---|---|---|---|
| BUG-001 | **P1** | Map | T1 | Merge PRs #2 #4 #1 #5 → Replay → the map is empty. `App.tsx` centres at -39.6265, 176.7253, but PR #4 moves the farm to about -39.584, 176.749 (5 km away). e2e: `0/10 on screen`. Fix: `fitBounds` to the farm GeoJSON. | Open: [#6](https://github.com/prasish01/highground/issues/6) |
| BUG-002 | P2 | Time | T3 | On main with the server on UTC: replay says "by 4am" (`+00:00`) instead of 5pm NZ. | Fix in PR #2 (verified): [#7](https://github.com/prasish01/highground/issues/7) |
| BUG-003 | P2 | Share | T1 | Branch `claude/nifty-bohr-q6fcnu`: `<SharePlan plan=… />` has no `isReplay`, so Copy as text in replay has no REPLAY line (hard rule 3). | Open: [#8](https://github.com/prasish01/highground/issues/8) |
| BUG-004 | P2 | API | T3 | PR #2: in replay mode, scores use the live HBRC gauge when `river_rising` is omitted (which the UI does), so the replay changes with the real river and waits on HBRC. | Open: [#9](https://github.com/prasish01/highground/issues/9) |
| BUG-005 | P2 | Plan | T3 | PR #2: with a key, every assess makes up to 2 Gemini calls with no timeout and no cache, so slow wifi stalls the Replay click. | Open: [#10](https://github.com/prasish01/highground/issues/10) |
| BUG-006 | P2 | Pitch | T4 (+T2) | `pitch.md` 0:50 says "a saved MetService warning", but the banner shows "SAMPLE: Red Heavy Rain Warning". | Open: [#11](https://github.com/prasish01/highground/issues/11) |
| BUG-007 | P3 | Map | T1 | Offline (no tiles) the map is a grey box behind the coloured paddocks. The wow still works, but there's no context. Consider pre-caching tiles for the demo area or a simple offline background. | Open |
| BUG-008 | P3 | Wording | T3 | Paddock 1 reason reads "-1 m above river" (PR #4 heights). Say "1 m below river" when the height is negative. | Open |
| BUG-009 | P3 | Map | T1 | The milking-shed circle is filled green by `style()` (fill defaults to green), so it looks like a safe paddock. Give the shed its own style. | Open |
| BUG-010 | P3 | Repo | Prasish | `web/tsconfig.tsbuildinfo` appears untracked after every `npm run build`. Add `*.tsbuildinfo` to `.gitignore`. | Open |
| BUG-011 | P3 | Repo | T4 / T1 | PR #1 adds `web/package-lock.json` (UI area). Good for reproducible installs, but anyone with a local untracked lock gets "untracked files would be overwritten" on merge (QA hit this). Agree it's kept, and T1 owns it. | Open |
| BUG-012 | P3 | Polish | T1 | The recommended paddock isn't marked on the map and paddock names only show on hover. On a projector, a label or outline on "Paddock 7" would make the move obvious. | Open |
| BUG-013 | P3 | Docs | T4 | README says "pytest # 16 tests" (now 120 on integration) and "Four Claude teammates" (there are five, plus QA). | Open |
| BUG-014 | P3 | Precision | T1 | Popup shows "risk 77/100", which suggests more precision than the rules have. Band words plus the reason are enough. (Judging angle: no false precision.) | Open |
| BUG-015 | P3 | PRs | T1 | PR #3 is fully contained in PR #5 (same 3 commits, plus more). Close #3 and merge #5. | Open |

## Resolved

| ID | Sev | What | How |
|---|---|---|---|
| — | P1 | PR #4 on hold: real heights + invented river gave no red paddocks | T2 redrew the farm beside the real Ngaruroro (commit 0958964). Now 3 red, 5 amber, 1 green. Verified by `tests/test_demo_path.py` on PR #4 alone. |
