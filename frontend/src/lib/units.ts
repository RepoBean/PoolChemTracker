// Unit conversion, mirroring backend/poolmath/units.py. Liquid volume (base
// fl oz) and dry weight (base oz); converting across the two is undefined.
const VOLUME: Record<string, number> = {
  fl_oz: 1, cup: 8, pint: 16, quart: 32, gal: 128, ml: 0.0338140227, l: 33.8140227,
};
const WEIGHT: Record<string, number> = {
  oz: 1, oz_wt: 1, lb: 16, g: 0.0352739619, kg: 35.2739619,
};

function table(u: string): Record<string, number> | null {
  if (u in VOLUME) return VOLUME;
  if (u in WEIGHT) return WEIGHT;
  return null;
}

export function convertUnit(amount: number, from: string, to: string): number | null {
  if (from === to) return amount;
  const t = table(from);
  if (!t || table(to) !== t) return null;
  return (amount * t[from]) / t[to];
}

// Units to offer for a computed dose, in a sensible order for its dimension.
export function unitOptions(u: string): string[] {
  if (u in VOLUME) return ["fl_oz", "cup", "quart", "gal"];
  if (u in WEIGHT) return ["oz_wt", "lb"];
  return [u];
}
