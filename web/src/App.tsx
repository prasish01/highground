import { useCallback, useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { Feature } from "geojson";
import { assess, getFarm, type Assessment, type Band, type Mode, type PaddockRisk } from "./api";
import About from "./components/About";
import SharePlan from "./components/SharePlan";

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

// Times: the UI never formats times itself. It shows the server's NZ-time labels
// (deadline_label, onset_label, expires_label) so every screen and the plan agree.

const SHED_STYLE = { color: "#333", weight: 2, fillColor: "#9aa0a6", fillOpacity: 1 };

/**
 * Zooms the map to fit the paddocks once the farm loads, so the farm can move (e.g. to the real
 * river) without changing code. The river line is left out: it can run far beyond the farm.
 * Extra bottom padding keeps paddocks clear of the legend when it floats over the map.
 */
function FitToFarm({ farm }: { farm: GeoJSON.FeatureCollection }) {
  const map = useMap();
  useEffect(() => {
    const paddocks = farm.features.filter((f) => f.properties?.kind !== "river");
    if (paddocks.length === 0) return;
    const bounds = L.geoJSON({ type: "FeatureCollection", features: paddocks } as GeoJSON.FeatureCollection).getBounds();
    if (!bounds.isValid()) return;
    const fit = () => {
      const legend = document.querySelector(".legend");
      const floating = legend && getComputedStyle(legend).position === "absolute";
      const legendH = floating ? (legend as HTMLElement).offsetHeight + 12 : 0;
      map.invalidateSize();
      map.fitBounds(bounds, { paddingTopLeft: [24, 24], paddingBottomRight: [24, 24 + legendH] });
    };
    fit();
    // Re-fit when the window changes size (rotate phone, projector resolution change).
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [farm, map]);
  return null;
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
    // Only paddocks get red/amber/green; the shed is neutral grey.
    if (kind === "shed") return SHED_STYLE;
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
          {/* The deadline is already in the message; this adds the warning window, using the
              server's NZ-time labels (never formatted here). */}
          {w.onset_label && (
            <div className="window">
              Warning {w.onset_label}
              {w.expires_label && <> – {w.expires_label}</>}
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
          {/* Starting view is all of NZ; FitToFarm zooms to the farm as soon as it loads. */}
          <MapContainer center={[-41, 174]} zoom={5} className="map">
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
                pointToLayer={(_f, latlng) => L.circleMarker(latlng, { radius: 8, ...SHED_STYLE })}
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
            {farm && <FitToFarm farm={farm} />}
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
              <div className="muted">{river.site}</div>
              {/* Server-formatted NZ time; shown only when the API sends it. */}
              {river.observed_label && <div className="muted">Read at {river.observed_label}</div>}
              {/* In replay the warning is a recording but the gauge is real and doesn't change
                  the scores (docs/decisions.md), so say so. */}
              {result?.mode === "replay" && (
                <div className="river-note">Live reading, not part of the replay</div>
              )}
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
              {/* Share first, so its REPLAY note is the first thing under the heading. */}
              <SharePlan plan={result.plan} isReplay={result.warning?.is_replay ?? false} />
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
            <About />
          </div>
        </div>
      )}
    </div>
  );
}
