import { useCallback, useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import L from "leaflet";
import type { Feature } from "geojson";
import { assess, getFarm, type Assessment, type Band, type Mode, type PaddockRisk } from "./api";
// TODO(teammate 4): when web/src/components/About.tsx and SharePlan.tsx land on main, replace
// the two fallbacks below with:
//   import About from "./components/About";
//   import SharePlan from "./components/SharePlan";
// and delete AboutFallback / SharePlanFallback at the bottom of this file.

// Always shown, even while loading or when the API is down (hard rule 1).
const SAFETY =
  "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee.";

const BAND_COLOUR: Record<Band, string> = { green: "#1f8a5b", amber: "#e0a526", red: "#d9363e" };
const BAND_LABEL: Record<Band, string> = {
  green: "Low risk – safe ground",
  amber: "Watch – could flood",
  red: "High risk – move stock out",
};

const API_DOWN =
  "Can't reach the HighGround server. Check the API is running (port 8000) and try again.";

// Times are always shown in NZ time, whatever the laptop's clock or time zone is set to.
const NZ_TIME = new Intl.DateTimeFormat("en-NZ", {
  timeZone: "Pacific/Auckland",
  hour: "numeric",
  minute: "2-digit",
});

/** "2026-11-21T03:00:00+00:00" -> "4:00 pm" in Pacific/Auckland (raw text if not a date). */
function clock(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return NZ_TIME.format(d);
}

/** Builds the paddock popup with DOM nodes (not an HTML string) so API text can't inject markup. */
function paddockPopup(name: string, risk: PaddockRisk | undefined): HTMLElement {
  const box = document.createElement("div");
  box.className = "popup";
  const h = document.createElement("strong");
  h.textContent = name;
  box.append(h);
  if (!risk) {
    const p = document.createElement("div");
    p.textContent = "No assessment yet.";
    box.append(p);
    return box;
  }
  const band = document.createElement("div");
  band.className = `popup-band popup-${risk.band}`;
  // score is 0–1 from risk.py; shown out of 100 so it reads easily.
  band.textContent = `${risk.band.toUpperCase()} · risk ${Math.round(risk.score * 100)}/100`;
  const reason = document.createElement("div");
  reason.textContent = risk.reason;
  box.append(band, reason);
  return box;
}

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

  const riskById = useMemo(() => {
    const m = new Map<string, PaddockRisk>();
    result?.paddocks.forEach((p) => m.set(p.paddock_id, p));
    return m;
  }, [result]);

  const style = (f?: Feature) => {
    const kind = f?.properties?.kind;
    if (kind === "river") return { color: "#1d5fd1", weight: 6 };
    const band = riskById.get(f?.properties?.id)?.band ?? "green";
    return { color: "#222", weight: 1.5, fillColor: BAND_COLOUR[band], fillOpacity: 0.6 };
  };

  const retry = useCallback(() => setAttempt((a) => a + 1), []);

  const w = result?.warning;
  const rec = result?.recommendation;
  const river = result?.river;
  const liveDown = result?.mode === "live" && result.live_status === "unavailable";

  return (
    <div className="app">
      {/* ---------- Hero banner ---------- */}
      {w ? (
        <header className={`banner banner-${w.level}`} role="alert">
          <div className="banner-top">
            {w.is_replay && <span className="tag-replay">REPLAY</span>}
            <span className="banner-level">{w.level.toUpperCase()} WARNING</span>
            <span className="banner-headline">{w.headline}</span>
          </div>
          {/* Main text is the server's own message, e.g. "Move the herd to <paddock> by 4pm". */}
          {rec && <div className="move">{rec.message}</div>}
          {rec?.deadline && (
            <div className="deadline">
              Deadline <strong>{clock(rec.deadline)}</strong> NZ time
              {w.onset && <> · warning starts {clock(w.onset)}</>}
            </div>
          )}
        </header>
      ) : liveDown ? (
        // Never show "all clear" when we simply couldn't check.
        <header className="banner banner-unavailable" role="alert">
          <div className="banner-top">
            <span className="banner-level">LIVE WARNINGS UNAVAILABLE</span>
          </div>
          <div className="move move-calm">Couldn't reach MetService. Check metservice.com</div>
        </header>
      ) : (
        <header className="banner banner-calm">
          <div className="banner-top">
            <span className="banner-level">
              {loading && !result
                ? "Loading…"
                : result?.mode === "live"
                  ? "No active warnings for this farm"
                  : "No warning – all clear"}
            </span>
          </div>
          {rec && <div className="move move-calm">{rec.message}</div>}
        </header>
      )}

      {/* ---------- Controls ---------- */}
      <nav className="controls">
        <button className="primary" onClick={() => setMode("replay")} aria-pressed={mode === "replay"}>
          Replay warning
        </button>
        <button onClick={() => setMode("live")} aria-pressed={mode === "live"}>
          Live mode
        </button>
        <button onClick={() => setMode("calm")} aria-pressed={mode === "calm"}>
          Reset
        </button>
        <button onClick={() => setShowPlan((s) => !s)} disabled={!result}>
          {showPlan ? "Hide plan" : "Show plan"}
        </button>
        <button onClick={() => setShowAbout(true)}>About</button>
        {loading && <span className="spinner" aria-live="polite">Updating…</span>}
      </nav>

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button onClick={retry}>Try again</button>
        </div>
      )}

      {/* ---------- Map + side panel ---------- */}
      <main className="layout">
        <div className="map-wrap">
          <MapContainer center={[-39.6265, 176.7253]} zoom={15} className="map">
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {farm && (
              <GeoJSON
                // Re-mount when scores change so colours and popups refresh.
                key={result ? JSON.stringify(result.paddocks) : "init"}
                data={farm}
                style={style}
                // Draw the shed as a circle (Leaflet's default pin images don't bundle with Vite).
                pointToLayer={(_f, latlng) =>
                  L.circleMarker(latlng, { radius: 8, color: "#222", fillColor: "#fff", fillOpacity: 1 })
                }
                onEachFeature={(f, layer) => {
                  const name = f.properties?.name;
                  if (!name) return;
                  layer.bindTooltip(name);
                  if (f.properties?.kind === "paddock") {
                    layer.bindPopup(paddockPopup(name, riskById.get(f.properties.id)));
                  }
                }}
              />
            )}
          </MapContainer>

          {!farm && (
            <div className="map-overlay">{error ? "Map unavailable" : "Loading farm map…"}</div>
          )}

          <div className="legend" aria-label="Map legend">
            {(Object.keys(BAND_COLOUR) as Band[]).map((b) => (
              <div key={b}>
                <span className="swatch" style={{ background: BAND_COLOUR[b] }} />
                {BAND_LABEL[b]}
              </div>
            ))}
            <div>
              <span className="swatch swatch-river" />
              River
            </div>
            <div className="muted">Tap a paddock for details</div>
          </div>
        </div>

        <aside className="side">
          {river && (
            <section className="river">
              <h2>River gauge</h2>
              <div className="river-level">
                {river.level_m.toFixed(2)} m{" "}
                <span className={river.rising ? "trend trend-rising" : "trend trend-steady"}>
                  {river.rising ? "▲ rising" : "● steady"}
                </span>
              </div>
              <div className="muted">
                {river.site} · read at {clock(river.observed_at)}
              </div>
            </section>
          )}

          {!result ? (
            <section>
              <p className="muted">{error ? "No data yet." : "Loading paddocks…"}</p>
            </section>
          ) : showPlan ? (
            <section>
              <h2>
                Storm plan {w?.is_replay && <span className="tag-replay small">REPLAY</span>}
              </h2>
              <p>{result.plan.summary}</p>
              <ol className="moves">
                {result.plan.moves.map((m, i) => (
                  <li key={i}>
                    <strong>{m.time}:</strong> {m.action}
                  </li>
                ))}
              </ol>
              <ul className="checklist">
                {result.plan.checklist.map((c, i) => (
                  <li key={i}>
                    <label>
                      <input type="checkbox" /> {c}
                    </label>
                  </li>
                ))}
              </ul>
              <SharePlanFallback plan={result.plan} isReplay={!!w?.is_replay} />
              <p className="muted">
                Written by: {result.plan.source === "gemini" ? "Gemini (from the facts above)" : "template"}
              </p>
            </section>
          ) : (
            <section>
              <h2>Paddocks</h2>
              <ul className="paddocks">
                {result.paddocks.map((p) => (
                  <li key={p.paddock_id}>
                    <span className="dot" style={{ background: BAND_COLOUR[p.band] }} />
                    <strong>{p.name}</strong> <span className="muted">{p.reason}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </main>

      <footer className="safety">{result?.disclaimer || SAFETY}</footer>

      {showAbout && (
        <div className="modal" role="dialog" aria-modal="true" onClick={() => setShowAbout(false)}>
          <div className="modal-body" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowAbout(false)} aria-label="Close">
              ×
            </button>
            <AboutFallback />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// TODO(teammate 4): temporary stand-ins. Delete once components/About.tsx and
// components/SharePlan.tsx exist on main, and use the imports at the top instead.
// ---------------------------------------------------------------------------

function AboutFallback() {
  return (
    <section>
      <h2>About HighGround</h2>
      <p>Turns severe weather warnings into a per-paddock plan for moving stock to higher ground.</p>
      <p>
        <strong>Data:</strong> MetService (warnings), LINZ via Open Topo Data (elevation), Hawke's Bay
        Regional Council (river levels), © OpenStreetMap contributors (base map).
      </p>
      <p>
        <strong>{SAFETY}</strong>
      </p>
    </section>
  );
}

function SharePlanFallback({ plan, isReplay }: { plan: Assessment["plan"]; isReplay: boolean }) {
  const [copied, setCopied] = useState(false);
  const text = [
    ...(isReplay ? ["REPLAY – practice warning, not a live alert"] : []),
    plan.summary, ...plan.moves.map((m) => `${m.time}: ${m.action}`), ...plan.checklist.map((c) => `- ${c}`), SAFETY].join("\n");
  return (
    <div className="share">
      <button
        onClick={() =>
          navigator.clipboard?.writeText(text).then(
            () => setCopied(true),
            () => setCopied(false),
          )
        }
      >
        {copied ? "Copied" : "Copy plan"}
      </button>
      <button onClick={() => window.print()}>Print</button>
    </div>
  );
}
