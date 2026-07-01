import { useEffect, useState } from "react";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { NoPool } from "../components/Empty";
import { Button, Card, ErrorText, NumberField, SelectField } from "../components/ui";
import type { Chemical, DoseResult, TestLog } from "../types";

const PARAMS = [
  { value: "fc", label: "Free Chlorine" },
  { value: "ph", label: "pH" },
  { value: "ta", label: "Total Alkalinity" },
  { value: "ch", label: "Calcium Hardness" },
  { value: "cya", label: "CYA (stabilizer)" },
  { value: "salt", label: "Salt" },
];

const CHEMS: Record<string, { value: string; label: string }[]> = {
  fc: [
    { value: "liquid_chlorine", label: "Liquid chlorine" },
    { value: "cal_hypo", label: "Cal-hypo" },
    { value: "dichlor", label: "Dichlor" },
  ],
  ph: [{ value: "muriatic_acid", label: "Muriatic acid (lower pH)" }],
  ta: [
    { value: "baking_soda", label: "Baking soda (raise)" },
    { value: "muriatic_acid", label: "Muriatic acid (lower)" },
  ],
  ch: [{ value: "calcium_chloride", label: "Calcium chloride" }],
  cya: [{ value: "cya_granular", label: "Stabilizer (CYA)" }],
  salt: [{ value: "pool_salt", label: "Pool salt" }],
};

const DEFAULT_STRENGTH: Record<string, string> = {
  liquid_chlorine: "12.5", cal_hypo: "73", dichlor: "56", muriatic_acid: "31.45", calcium_chloride: "dihydrate",
};

const LATEST_KEY: Record<string, keyof TestLog> = { fc: "fc", ph: "ph", ta: "ta", ch: "ch", cya: "cya", salt: "salt" };

export default function Dosing() {
  const { current } = usePools();
  const [param, setParam] = useState("fc");
  const [chemical, setChemical] = useState("liquid_chlorine");
  const [cur, setCur] = useState<number | null>(null);
  const [goal, setGoal] = useState<number | null>(null);
  const [ta, setTa] = useState<number | null>(80);
  const [strength, setStrength] = useState("12.5");
  const [volume, setVolume] = useState<number | null>(null);
  const [result, setResult] = useState<DoseResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [inv, setInv] = useState<Chemical[]>([]);
  const [invId, setInvId] = useState("");
  const [latest, setLatest] = useState<TestLog | null>(null);
  const [logged, setLogged] = useState(false);

  useEffect(() => {
    if (!current) return;
    setVolume(current.volume_gal);
    api.listChemicals(current.id).then(setInv).catch(() => {});
    api.listTests(current.id).then((ts) => setLatest(ts.length ? ts[ts.length - 1] : null)).catch(() => {});
  }, [current]);

  useEffect(() => {
    const c = CHEMS[param][0].value;
    setChemical(c);
    setStrength(DEFAULT_STRENGTH[c] ?? "");
    setResult(null);
    setLogged(false);
  }, [param]);

  if (!current) return <NoPool />;

  const showStrengthNumber = ["liquid_chlorine", "cal_hypo", "dichlor", "muriatic_acid"].includes(chemical);
  const showForm = chemical === "calcium_chloride";
  const needsTa = param === "ph";

  function pickChemical(c: string) {
    setChemical(c);
    setStrength(DEFAULT_STRENGTH[c] ?? "");
    setResult(null);
    setLogged(false);
  }

  function useLatest() {
    const k = LATEST_KEY[param];
    if (latest && k && latest[k] != null) setCur(Number(latest[k]));
    if (latest && latest.ta != null) setTa(Number(latest.ta));
  }

  async function compute() {
    setErr(null);
    setLogged(false);
    try {
      const body: Record<string, unknown> = {
        parameter: param, chemical, current: cur ?? 0, goal: goal ?? 0,
        volume_gal: volume ?? current!.volume_gal, strength,
      };
      if (needsTa) body.total_alkalinity = ta;
      setResult(await api.dose(body));
    } catch (e) {
      setErr(String(e));
    }
  }

  async function logDose() {
    if (!result) return;
    try {
      await api.logDose(current!.id, {
        chemical: result.chemical, amount: result.amount, unit: result.unit,
        parameter_targeted: param, from_value: cur, to_value: goal,
        chemical_id: invId ? Number(invId) : null,
      });
      setLogged(true);
      if (invId) api.listChemicals(current!.id).then(setInv).catch(() => {});
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Dosing</h1>
      <Card className="space-y-3">
        <SelectField label="Parameter" value={param} onChange={setParam} options={PARAMS} />
        <SelectField label="Chemical" value={chemical} onChange={pickChemical} options={CHEMS[param]} />
        <div className="grid grid-cols-2 gap-3">
          <NumberField label="Current" value={cur} onChange={setCur} />
          <NumberField label="Goal" value={goal} onChange={setGoal} />
        </div>
        {latest && (
          <button onClick={useLatest} className="text-sky-600 text-sm">↧ Use current from latest test</button>
        )}
        {needsTa && <NumberField label="Total Alkalinity (buffers acid)" unit="ppm" step="1" value={ta} onChange={setTa} />}
        <div className="grid grid-cols-2 gap-3">
          {showStrengthNumber && (
            <NumberField label="Strength %" value={strength === "" ? null : Number(strength)} step="0.05"
              onChange={(v) => setStrength(v == null ? "" : String(v))} />
          )}
          {showForm && (
            <SelectField label="Form" value={strength} onChange={setStrength}
              options={[{ value: "dihydrate", label: "Dihydrate (77%)" }, { value: "anhydrous", label: "Anhydrous (100%)" }]} />
          )}
          <NumberField label="Volume" unit="gal" step="100" value={volume} onChange={setVolume} />
        </div>
        <ErrorText msg={err} />
        <Button className="w-full" onClick={compute}>Calculate dose</Button>
      </Card>

      {result && (
        <Card className="space-y-3">
          {result.amount > 0 ? (
            <div className="text-center">
              <div className="text-4xl font-bold text-sky-700">
                {result.amount} <span className="text-lg font-normal">{result.unit}</span>
              </div>
              <div className="text-sm text-slate-500">{result.chemical.replace(/_/g, " ")}</div>
            </div>
          ) : (
            <div className="text-center text-slate-600">{result.note || "No chemical addition needed."}</div>
          )}

          {result.amount > 0 && Object.keys(result.side_effects).length > 0 && (
            <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl p-2">
              Side effects: {Object.entries(result.side_effects).map(([k, v]) => `${k.toUpperCase()} +${v}`).join(", ")}
            </div>
          )}
          {result.amount > 0 && result.note && <p className="text-xs text-slate-500">{result.note}</p>}

          {result.amount > 0 && (
            <>
              {inv.length > 0 && (
                <SelectField label="Draw from inventory (optional)" value={invId} onChange={setInvId}
                  options={[{ value: "", label: "— none —" },
                    ...inv.map((c) => ({ value: String(c.id), label: `${c.name} (${c.qty_on_hand} ${c.unit})` }))]} />
              )}
              <Button variant="ghost" className="w-full" onClick={logDose} disabled={logged}>
                {logged ? "Logged ✓" : "Log this dose"}
              </Button>
            </>
          )}
        </Card>
      )}
    </div>
  );
}
