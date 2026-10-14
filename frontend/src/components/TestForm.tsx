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

// OTO 5-drop swatch steps (TFP's standard set). "none" = no color change
// (FC < 0.5); the ramp deepens one notch per step. Value maps to the numeric
// FC lower bound on the backend.
const FC_SWATCHES: { value: string; label: string; color: string | null }[] = [
  { value: "none", label: "no color", color: null },
  { value: "0.5", label: "0.5", color: "#fde8f1" },
  { value: "1", label: "1", color: "#fbcfe0" },
  { value: "2", label: "2", color: "#f7a8cb" },
  { value: "3", label: "3", color: "#f37fb5" },
  { value: "5", label: "5", color: "#ee539b" },
  { value: "10", label: "10", color: "#e02a80" },
  { value: "15", label: "15", color: "#c61d6d" },
  { value: "20", label: "20", color: "#a7155a" },
  { value: "30", label: "30", color: "#8b0e4a" },
  { value: "40", label: "40", color: "#71083b" },
  { value: "50", label: "50", color: "#59032c" },
  { value: "100", label: "100", color: "#41021f" },
];

const PH_CHIPS = ["7.2", "7.4", "7.6", "7.8", "8.0", "8.2", "8.4"];

const MODE_KEY = "poolmath.testMode";
type Mode = "full" | "quick";

function initialMode(): Mode {
  try {
    const m = localStorage.getItem(MODE_KEY);
    return m === "quick" || m === "full" ? m : "full";
  } catch {
    return "full";
  }
}

export function TestForm({ onSaved }: { onSaved?: (r: LogTestResult) => void }) {
  const { current, refresh } = usePools();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [f, setF] = useState<Form>(EMPTY);
  const [fcColor, setFcColor] = useState<string | null>(null);
  const [phQuick, setPhQuick] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<LogTestResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (!current) return null;
  const set = (k: string) => (v: number | null) => setF((s) => ({ ...s, [k]: v }));
  const hasReading =
    mode === "full"
      ? Object.values(f).some((v) => v != null)
      : fcColor != null || phQuick != null;

  function switchMode(m: Mode) {
    setMode(m);
    try { localStorage.setItem(MODE_KEY, m); } catch { /* private mode */ }
  }

  async function save() {
    setSaving(true);
    setErr(null);
    try {
      const body = mode === "quick"
        ? { test_type: "quick", fc_color: fcColor, ph_quick: phQuick }
        : { ...f, notes: notes || null };
      const r = await api.logTest(current!.id, body);
      setResult(r);
      setF(EMPTY); setFcColor(null); setPhQuick(null); setNotes("");
      await refresh();
      onSaved?.(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  const fcLabel = fcColor
    ? FC_SWATCHES.find((s) => s.value === fcColor)?.label ?? fcColor
    : null;

  return (
    <div className="space-y-3">
      {/* Mode toggle — remembers the last-used mode. */}
      <div className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1 text-sm">
        {(["full", "quick"] as Mode[]).map((m) => (
          <button key={m} type="button" onClick={() => switchMode(m)}
            className={`rounded-lg px-3 py-1.5 font-medium transition ${
              mode === m ? "bg-white shadow text-sky-700" : "text-slate-500"}`}>
            {m === "full" ? "Full test" : "Quick test"}
          </button>
        ))}
      </div>

      {mode === "full" ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <NumberField label="FC" unit="ppm" min={0} value={f.fc} onChange={set("fc")} />
            <NumberField label="pH" value={f.ph} step="0.1" min={0} onChange={set("ph")} />
            <NumberField label="CC" unit="ppm" min={0} value={f.cc} onChange={set("cc")} />
            <NumberField label="TA" unit="ppm" step="1" min={0} value={f.ta} onChange={set("ta")} />
            <NumberField label="CH" unit="ppm" step="5" min={0} value={f.ch} onChange={set("ch")} />
            <NumberField label="CYA" unit="ppm" step="1" min={0} value={f.cya} onChange={set("cya")} />
            {current.uses_salt && <NumberField label="Salt" unit="ppm" step="10" min={0} value={f.salt} onChange={set("salt")} />}
            {current.uses_borates && <NumberField label="Borate" unit="ppm" step="1" min={0} value={f.borate} onChange={set("borate")} />}
            <NumberField label="Temp" unit="°F" step={1} min={0} value={f.water_temp_f} onChange={set("water_temp_f")} />
          </div>
          <TextField label="Notes" value={notes} onChange={setNotes} placeholder="Optional" />
        </>
      ) : (
        <div className="space-y-3">
          <div>
            <div className="text-sm text-slate-600 mb-1.5">
              Chlorine (OTO 5-drop)
              {fcLabel != null && (
                <span className="ml-2 font-semibold text-sky-700">
                  FC ≈ {fcLabel === "no color" ? "< 0.5" : fcLabel} ppm
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {FC_SWATCHES.map((s) => (
                <button
                  key={s.value} type="button"
                  onClick={() => setFcColor(fcColor === s.value ? null : s.value)}
                  title={s.value === "none" ? "No color change (FC < 0.5)" : `FC ≈ ${s.label} ppm`}
                  aria-label={s.value === "none" ? "no color" : s.label}
                  className={`flex h-9 w-9 flex-col items-center justify-center rounded-lg border text-[10px] leading-none transition active:scale-95 ${
                    fcColor === s.value
                      ? "border-sky-600 ring-2 ring-sky-400"
                      : "border-slate-300"
                  }`}
                  style={{
                    backgroundColor: s.color ?? "#ffffff",
                    borderStyle: s.color ? "solid" : "dashed",
                    color: s.color && Number(s.value) >= 5 ? "#fff" : "#334155",
                  }}>
                  {s.value === "none" ? "–" : s.label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-sm text-slate-600 mb-1.5">
              pH (strip / drop)
              {phQuick != null && <span className="ml-2 font-semibold text-violet-700">{phQuick}</span>}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {PH_CHIPS.map((p) => (
                <button
                  key={p} type="button"
                  onClick={() => setPhQuick(phQuick === p ? null : p)}
                  className={`rounded-lg px-2.5 py-2 text-sm font-medium transition active:scale-95 ${
                    phQuick === p
                      ? "bg-violet-600 text-white ring-2 ring-violet-300"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <ErrorText msg={err} />
      <Button className="w-full" onClick={save} disabled={saving || !hasReading}>
        {saving ? "Saving…" : mode === "quick" ? "Save quick test" : "Save full test"}
      </Button>

      {result && (
        <div className="space-y-2 pt-1">
          {result.test.csi != null && (
            <div className="text-sm">Saved ✓ · CSI <b>{result.test.csi}</b> ({result.csi_status})</div>
          )}
          {result.test.csi == null && (
            <div className="text-sm">
              Saved ✓
              {result.test.is_approx
                ? ` · FC ≈ ${result.test.fc ?? "—"} (quick test)`
                : " · full test"}
            </div>
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
