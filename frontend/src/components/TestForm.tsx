import { useState } from "react";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { Button, ErrorText, NumberField, TextField } from "./ui";
import type { LogTestResult } from "../types";

type Form = Record<string, number | null>;
const EMPTY: Form = {
  fc: null, cc: null, ph: null, ta: null, ch: null, cya: null, salt: null, borate: null, water_temp_f: null,
};

const recColors: Record<string, string> = {
  ok: "border-green-200 bg-green-50 text-green-800",
  info: "border-sky-200 bg-sky-50 text-sky-800",
  warn: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-red-200 bg-red-50 text-red-800",
};

export function TestForm({ onSaved }: { onSaved?: (r: LogTestResult) => void }) {
  const { current, refresh } = usePools();
  const [f, setF] = useState<Form>(EMPTY);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<LogTestResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!current) return null;
  const set = (k: string) => (v: number | null) => setF((s) => ({ ...s, [k]: v }));

  async function save() {
    setSaving(true);
    setErr(null);
    try {
      const r = await api.logTest(current!.id, { ...f, notes: notes || null });
      setResult(r);
      setF(EMPTY);
      setNotes("");
      await refresh();
      onSaved?.(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <NumberField label="FC" unit="ppm" value={f.fc} onChange={set("fc")} />
        <NumberField label="pH" value={f.ph} step="0.1" onChange={set("ph")} />
        <NumberField label="CC" unit="ppm" value={f.cc} onChange={set("cc")} />
        <NumberField label="TA" unit="ppm" step="1" value={f.ta} onChange={set("ta")} />
        <NumberField label="CH" unit="ppm" step="5" value={f.ch} onChange={set("ch")} />
        <NumberField label="CYA" unit="ppm" step="1" value={f.cya} onChange={set("cya")} />
        {current.uses_salt && <NumberField label="Salt" unit="ppm" step="10" value={f.salt} onChange={set("salt")} />}
        {current.uses_borates && <NumberField label="Borate" unit="ppm" step="1" value={f.borate} onChange={set("borate")} />}
        <NumberField label="Temp" unit="°F" step="1" value={f.water_temp_f} onChange={set("water_temp_f")} />
      </div>
      <TextField label="Notes" value={notes} onChange={setNotes} placeholder="Optional" />
      <ErrorText msg={err} />
      <Button className="w-full" onClick={save} disabled={saving}>
        {saving ? "Saving…" : "Save test"}
      </Button>

      {result && (
        <div className="space-y-2 pt-1">
          {result.test.csi != null && (
            <div className="text-sm">Saved ✓ · CSI <b>{result.test.csi}</b> ({result.csi_status})</div>
          )}
          {result.recommendation && (
            <div className={`rounded-xl border p-2.5 text-sm ${recColors[result.recommendation.level] ?? recColors.info}`}>
              {result.recommendation.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
