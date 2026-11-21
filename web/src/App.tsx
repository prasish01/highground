import { useCallback, useEffect, useMemo, useState } from "react";
import "@fontsource/bricolage-grotesque/600.css";
import "@fontsource/bricolage-grotesque/800.css";
import "@fontsource/atkinson-hyperlegible/400.css";
import "@fontsource/atkinson-hyperlegible/700.css";
import "@fontsource/saira-stencil-one/400.css";
import { assess, getFarm, type Assessment, type Band, type Mode, type PaddockRisk } from "./api";
import { BAND_WORDS } from "./bands";
import About from "./components/About";
import FarmMap from "./components/FarmMap";
import SharePlan from "./components/SharePlan";

// Always shown, even while loading or when the API is down (hard rule 1).
const SAFETY =
  "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee.";

const API_DOWN =
  "Can't reach the HighGround server. Check the API is running (port 8000) and try again.";

// Times: the UI never formats times itself. It shows the server's NZ-time labels
// (deadline_label, onset_label, expires_label) so every screen and the plan agree.

const LEGEND: Record<Band, string> = { red: "high risk", amber: "could flood", green: "low risk" };

const LEVEL_WORD: Record<string, string> = { red: "Red", orange: "Orange", yellow: "Yellow" };

export default function App() {
  const [farm, setFarm] = useState<GeoJSON.FeatureCollection | null>(null);
  const [mode, setMode] = useState<Mode>("calm");
  const [result, setResult] = useState<Assessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [showPlan, setShowPlan] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0); // bump to retry after an error

  useEffect(() => {
    getFarm()
      .then(setFarm)
      .catch(() => setError(API_DOWN));
  }, [attempt]);

  useEffect(() => {
    let current = true; // ignore slow answers if the user has already clicked another mode
    setLoading(true);
    setError(null);
    assess(mode)
      .then((r) => current && setResult(r))
      .catch((e) => {
        if (!current) return;
        // A 502 in live mode means MetService was unreachable, not our server.
        const msg = String(e);
        setError(
          mode === "live" && msg.includes("502")
            ? "Couldn't reach the MetService warnings feed. Try Replay warning for the demo."
            : API_DOWN,
        );
      })
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
  }, [mode, attempt]);

  useEffect(() => {
    if (!showAbout) return;
    const close = (e: KeyboardEvent) => e.key === "Escape" && setShowAbout(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [showAbout]);

  const riskById = useMemo(() => {
    const m = new Map<string, PaddockRisk>();
    result?.paddocks.forEach((p) => m.set(p.paddock_id, p));
    return m;
  }, [result]);

  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  const w = result?.warning;
  const rec = result?.recommendation;
  const river = result?.river;
  const liveDown = result?.mode === "live" && result.live_status === "unavailable";

  return (
    <div className="app">
      {/* ---------- Header: name and the modes ---------- */}
      <header className="topbar">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 40 28" aria-hidden="true">
            <path d="M2 24 Q10 6 18 14 Q24 2 38 24" />
            <path d="M2 24 H38" />
            <path className="brand-water" d="M4 26 Q8 24 12 26 T20 26 T28 26 T36 26" />
          </svg>
          <span className="brand-name">HighGround</span>
        </div>
        <nav className="controls" aria-label="Mode">
          <button className="btn btn-primary" onClick={() => setMode("replay")} aria-pressed={mode === "replay"}>
            Replay warning
          </button>
          <button className="btn" onClick={() => setMode("live")} aria-pressed={mode === "live"}>
            Live mode
          </button>
          <button className="btn" onClick={() => setMode("calm")} aria-pressed={mode === "calm"}>
            Reset
          </button>
          <button className="btn" onClick={() => setShowPlan((s) => !s)} disabled={!result} aria-pressed={showPlan}>
            {showPlan ? "Hide plan" : "Show plan"}
          </button>
          <button className="btn btn-quiet" onClick={() => setShowAbout(true)}>
            About
          </button>
        </nav>
      </header>

      {/* ---------- The instruction: the loudest thing on screen ---------- */}
      {w ? (
        <section className={`banner banner-${w.level}`} role="alert">
          <div className="banner-top">
            {w.is_replay && <span className="tag-replay">REPLAY</span>}
            <span className="banner-level">{LEVEL_WORD[w.level] ?? w.level} warning</span>
            <span className="banner-headline">{w.headline}</span>
          </div>
          {/* Main text is the server's own message, e.g. "Move the herd to <paddock> by 4pm". */}
          {rec && <p className="move">{rec.message}</p>}
          {w.onset_label && (
            <p className="window">
              Warning in force {w.onset_label}
              {w.expires_label && <> to {w.expires_label}</>}
            </p>
          )}
        </section>
      ) : liveDown ? (
        // Never show "all clear" when we simply couldn't check.
        <section className="banner banner-unavailable" role="alert">
          <div className="banner-top">
            <span className="banner-level">Live warnings unavailable</span>
          </div>
          <p className="move move-calm">Couldn't reach MetService. Check metservice.com</p>
        </section>
      ) : (
        <section className="banner banner-calm" aria-live="polite">
          <div className="banner-top">
            <span className="banner-level">
              {loading && !result
                ? "Checking the farm…"
                : result?.mode === "live"
                  ? "No active warnings for this farm"
                  : "No warning, all clear"}
            </span>
          </div>
          {rec && <p className="move move-calm">{rec.message}</p>}
        </section>
      )}

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="btn btn-small" onClick={retry}>
            Try again
          </button>
        </div>
      )}

      {/* ---------- Map + side sheet ---------- */}
      <main className={`layout${loading ? " is-loading" : ""}`}>
        <section className="map-card" aria-label="Farm map">
          {farm ? (
            <FarmMap farm={farm} risks={riskById} stamped={Boolean(w)} herdTo={w ? rec?.paddock_id : null} />
          ) : (
            <p className="map-empty">{error ? "The farm map can't load without the server." : "Drawing the farm…"}</p>
          )}
          <ul className="legend" aria-label="Map legend">
            {(["red", "amber", "green"] as Band[]).map((b) => (
              <li key={b}>
                <span className={`legend-wash wash-${b}`} aria-hidden="true" />
                <span className={`chip chip-${b}`}>{BAND_WORDS[b].stamp}</span>
                <span className="legend-words">{LEGEND[b]}</span>
              </li>
            ))}
            <li className="legend-hint">Tap a paddock to see why</li>
          </ul>
        </section>

        <aside className="sheet">
          {river && (
            <section className="river-panel">
              <h2>River gauge</h2>
              <p className="river-level">
                <span className="num">{river.level_m.toFixed(2)}</span> m
                <span className={river.rising ? "trend trend-rising" : "trend trend-steady"}>
                  <svg viewBox="0 0 16 16" aria-hidden="true">
                    {river.rising ? <path d="M3 12 L8 4 L13 12" /> : <path d="M2 9 Q5 6 8 8 T14 7" />}
                  </svg>
                  {river.rising ? "rising" : "steady"}
                </span>
              </p>
              <p className="muted">{river.site}</p>
              {/* Server-formatted NZ time; shown only when the API sends it. */}
              {river.observed_label && <p className="muted">Read at {river.observed_label}</p>}
              {/* In replay the warning is a recording but the gauge is real and doesn't change
                  the scores (docs/decisions.md), so say so. */}
              {result?.mode === "replay" && <p className="river-note">Live reading, not part of the replay</p>}
            </section>
          )}

          {!result ? (
            <section>
              <p className="muted">{error ? "No data yet." : "Loading paddocks…"}</p>
            </section>
          ) : showPlan ? (
            <section className="plan">
              <h2>
                Storm plan {w?.is_replay && <span className="tag-replay small">REPLAY</span>}
              </h2>
              {/* Share first, so its REPLAY note is the first thing under the heading. */}
              <SharePlan plan={result.plan} isReplay={result.warning?.is_replay ?? false} />
              <p className="plan-summary">{result.plan.summary}</p>
              <ol className="moves">
                {result.plan.moves.map((m, i) => (
                  <li key={i}>
                    <span className="move-time">{m.time}</span> {m.action}
                  </li>
                ))}
              </ol>
              <ul className="checklist">
                {result.plan.checklist.map((c, i) => (
                  <li key={i}>
                    <label>
                      <input type="checkbox" /> <span>{c}</span>
                    </label>
                  </li>
                ))}
              </ul>
              <p className="muted">
                Written by {result.plan.source === "gemini" ? "Gemini, from the facts above" : "the plan template"}
              </p>
            </section>
          ) : (
            <section>
              <h2>Paddocks</h2>
              <ul className="paddocks">
                {result.paddocks.map((p) => (
                  <li key={p.paddock_id}>
                    <span className={`chip chip-${p.band}`}>{BAND_WORDS[p.band].stamp}</span>
                    <span className="paddock-row">
                      <strong>{p.name}</strong>
                      <span className="muted">{p.reason}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </main>

      <footer className="safety">{result?.disclaimer || SAFETY}</footer>

      {showAbout && (
        <div className="modal" role="dialog" aria-modal="true" aria-label="About HighGround" onClick={() => setShowAbout(false)}>
          <div className="modal-body" onClick={(e) => e.stopPropagation()}>
            <button className="card-close" onClick={() => setShowAbout(false)} aria-label="Close">
              <svg viewBox="0 0 16 16" aria-hidden="true">
                <path d="M3 3 L13 13 M13 3 L3 13" />
              </svg>
            </button>
            <About />
          </div>
        </div>
      )}
    </div>
  );
}
