// What each risk band is called and what ink it is stamped in. Shared by the map, list and legend.
import type { Band } from "./api";

export const BAND_WORDS: Record<Band, { stamp: string; long: string }> = {
  red: { stamp: "MOVE OUT", long: "high risk, move stock out" },
  amber: { stamp: "WATCH", long: "watch, could flood" },
  green: { stamp: "SAFE", long: "low risk, safe ground" },
};

/** Stamp ink per band (also used for chips). Wash colours live in styles.css. */
export const BAND_STAMP: Record<Band, string> = {
  red: "#b3261e",
  amber: "#8f5a00",
  green: "#2c6b3c",
};
