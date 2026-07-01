import type { Targets } from "../types";

// "high" = above target but still safe (FC up to SLAM). It's intentionally NOT
// red — TFP: FC up to SLAM level is safe to swim. "too_high" is the opposite:
// above the acceptable max for a param where that's a problem (pH, TA, CH, CYA),
// so it's red like "low" — both directions out of range.
export type Status =
  | "low" | "acceptable_low" | "ideal" | "acceptable_high" | "high" | "too_high" | "unknown";

export function statusClasses(s: Status): string {
  switch (s) {
    case "low":
    case "too_high":
      return "bg-red-50 text-red-700 border-red-300";
    case "acceptable_low":
    case "acceptable_high":
      return "bg-amber-50 text-amber-700 border-amber-300";
    case "ideal":
      return "bg-green-50 text-green-700 border-green-300";
    case "high":
      return "bg-sky-50 text-sky-700 border-sky-300";
    default:
      return "bg-slate-50 text-slate-500 border-slate-200";
  }
}

export function dotClasses(s: Status): string {
  switch (s) {
    case "low":
    case "too_high":
      return "bg-red-500";
    case "acceptable_low":
    case "acceptable_high":
      return "bg-amber-500";
    case "ideal":
      return "bg-green-500";
    case "high":
      return "bg-sky-500";
    default:
      return "bg-slate-300";
  }
}

export function fcStatus(fc: number | null | undefined, t: Targets | null): Status {
  if (fc == null || !t) return "unknown";
  if (fc < t.min_fc) return "low";
  if (fc < t.target_fc_low) return "acceptable_low";
  if (fc <= t.target_fc_high) return "ideal";
  return "high"; // above target but safe up to SLAM
}

export function phStatus(ph: number | null | undefined): Status {
  if (ph == null) return "unknown";
  if (ph < 7.2 || ph > 8.0) return ph < 7.2 ? "low" : "too_high";
  if (ph < 7.6) return "acceptable_low";
  if (ph <= 7.8) return "ideal";
  return "acceptable_high";
}

export function csiStatus(csiStatusStr: string | null | undefined): Status {
  switch (csiStatusStr) {
    case "etching":
      return "low";
    case "acceptable_low":
      return "acceptable_low";
    case "ideal":
      return "ideal";
    case "acceptable_high":
      return "acceptable_high";
    case "scaling":
      return "low"; // out-of-range (like etching) -> red; both extremes are problems
    default:
      return "unknown";
  }
}

// generic band classifier: (min, idealLow, idealHigh, max)
export function bandStatus(
  v: number | null | undefined,
  min: number, idealLow: number, idealHigh: number, max: number,
): Status {
  if (v == null) return "unknown";
  if (v < min || v > max) return v < min ? "low" : "too_high";
  if (v < idealLow) return "acceptable_low";
  if (v <= idealHigh) return "ideal";
  return "acceptable_high";
}
