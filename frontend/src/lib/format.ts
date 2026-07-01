// Display helpers. Backend units are machine-ish tokens (fl_oz, oz_wt); render
// them the way you'd read a dosing instruction out loud.
const UNIT_LABELS: Record<string, string> = {
  fl_oz: "fl oz",
  oz_wt: "oz",
  oz: "oz",
  lb: "lb",
  ppm: "ppm",
  gal: "gal",
  cup: "cup",
  pint: "pt",
  quart: "qt",
  ml: "mL",
  l: "L",
  g: "g",
  kg: "kg",
};

export function prettyUnit(u: string | null | undefined): string {
  if (!u) return "";
  return UNIT_LABELS[u] ?? u.replace(/_/g, " ");
}

export function money(n: number | null | undefined): string {
  return n == null ? "—" : `$${n.toFixed(2)}`;
}
