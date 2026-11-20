import { useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { Feature } from "geojson";
import { assess, getFarm, type Assessment, type Band, type Mode } from "./api";

const BAND_COLOUR: Record<Band, string> = { green: "#2e9e6b", amber: "#e0a526", red: "#d9503f" };

export default function App() {
  const [farm, setFarm] = useState<GeoJSON.FeatureCollection | null>(null);
  const [mode, setMode] = useState<Mode>("calm");
  const [result, setResult] = useState<Assessment | null>(null);
  const [showPlan, setShowPlan] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFarm().then(setFarm).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    setError(null);
    assess(mode).then(setResult).catch((e) => setError(String(e)));
  }, [mode]);

  const bandById = useMemo(() => {
    const m = new Map<string, Band>();
    result?.paddocks.forEach((p) => m.set(p.paddock_id, p.band));
    return m;
  }, [result]);

  const style = (f?: Feature) => {
    const kind = f?.properties?.kind;
    if (kind === "river") return { color: "#2f6fd6", weight: 5 };
    const band = bandById.get(f?.properties?.id) ?? "green";
    return { color: "#333", weight: 1, fillColor: BAND_COLOUR[band], fillOpacity: 0.55 };
  };

  const w = result?.warning;

  return (
    <div className="app">
      {w && (
        <div className={`banner banner-${w.level}`}>
          <strong>{w.is_replay ? "REPLAY · " : ""}{w.headline}</strong>
          {result?.recommendation && <div className="move">{result.recommendation.message}</div>}
        </div>
      )}

      <div className="controls">
        <button onClick={() => setMode("replay")}>Replay warning</button>
        <button onClick={() => setMode("live")}>Live mode</button>
        <button onClick={() => setMode("calm")}>Reset</button>
        <button onClick={() => setShowPlan((s) => !s)}>{showPlan ? "Hide plan" : "Show plan"}</button>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="layout">
        <MapContainer center={[-39.6265, 176.7253]} zoom={15} className="map">
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {farm && (
            <GeoJSON
              key={result ? JSON.stringify([...bandById]) : "init"}
              data={farm}
              style={style}
              onEachFeature={(f, layer) => f.properties?.name && layer.bindTooltip(f.properties.name)}
            />
          )}
        </MapContainer>

        <aside className="side">
          {showPlan && result ? (
            <section>
              <h2>Storm plan</h2>
              <p>{result.plan.summary}</p>
              <ol>
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
              <button onClick={() => window.print()}>Print / share</button>
              <p className="muted">Written by: {result.plan.source}</p>
            </section>
          ) : (
            <section>
              <h2>Paddocks</h2>
              <ul className="paddocks">
                {result?.paddocks.map((p) => (
                  <li key={p.paddock_id}>
                    <span className="dot" style={{ background: BAND_COLOUR[p.band] }} />
                    <strong>{p.name}</strong> <span className="muted">{p.reason}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>

      <footer>{result?.disclaimer}</footer>
    </div>
  );
}
