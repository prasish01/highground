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
}

export async function getFarm(): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch("/api/farm");
  if (!res.ok) throw new Error(`Farm request failed: ${res.status}`);
  return res.json();
}

export async function assess(mode: Mode, riverRising = false): Promise<Assessment> {
  const res = await fetch(`/api/assess?mode=${mode}&river_rising=${riverRising}`);
  if (!res.ok) throw new Error(`Assessment failed: ${res.status}`);
  return res.json();
}
