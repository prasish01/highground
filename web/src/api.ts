export type Band = "green" | "amber" | "red";
export type Mode = "calm" | "replay" | "live";

export interface PaddockRisk {
  paddock_id: string;
  name: string;
  score: number;
  band: Band;
  reason: string;
  height_above_river_m: number;
  distance_to_river_m: number;
}

export interface RiverReading {
  site: string;
  level_m: number;
  observed_at: string;
  rising: boolean;
}

export interface Assessment {
  mode: Mode;
  warning: null | {
    event: string;
    headline: string;
    level: "yellow" | "orange" | "red";
    onset: string;
    expires: string;
    is_replay: boolean;
  };
  paddocks: PaddockRisk[];
  recommendation: null | { name: string; message: string; deadline: string | null };
  plan: {
    summary: string;
    moves: { time: string; action: string }[];
    checklist: string[];
    source: "gemini" | "template";
  };
  disclaimer: string;
  /** Optional: river gauge reading. May be missing or null (e.g. gauge offline). */
  river?: RiverReading | null;
  /** Live mode only: "ok" if the MetService feed answered, "unavailable" if not; null otherwise. */
  live_status?: "ok" | "unavailable" | null;
  /** Whether scoring treated the river as rising (from the gauge, or the query parameter). */
  river_rising?: boolean;
}

export async function getFarm(): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch("/api/farm");
  if (!res.ok) throw new Error(`Farm request failed: ${res.status}`);
  return res.json();
}

/**
 * riverRising is only sent when given. Leaving it out lets the server use the real river gauge;
 * sending false would override the gauge.
 */
export async function assess(mode: Mode, riverRising?: boolean): Promise<Assessment> {
  const params = new URLSearchParams({ mode });
  if (riverRising !== undefined) params.set("river_rising", String(riverRising));
  const res = await fetch(`/api/assess?${params}`);
  if (!res.ok) throw new Error(`Assessment failed: ${res.status}`);
  return res.json();
}
