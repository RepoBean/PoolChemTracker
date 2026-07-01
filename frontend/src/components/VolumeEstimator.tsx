import { useState } from "react";
import { api } from "../api";
import { Button, ErrorText, Modal, NumberField, SelectField } from "./ui";

const shapes = [
  { value: "rectangular", label: "Rectangle" },
  { value: "round", label: "Round" },
  { value: "oval", label: "Oval" },
  { value: "kidney", label: "Kidney" },
  { value: "freeform", label: "Freeform" },
];

export function VolumeEstimator({
  open, onClose, onUse,
}: {
  open: boolean; onClose: () => void; onUse: (gallons: number) => void;
}) {
  const [shape, setShape] = useState("rectangular");
  const [length, setLength] = useState<number | null>(32);
  const [width, setWidth] = useState<number | null>(16);
  const [avgDepth, setAvgDepth] = useState<number | null>(5.5);
  const [useSlope, setUseSlope] = useState(false);
  const [shallow, setShallow] = useState<number | null>(3);
  const [deep, setDeep] = useState<number | null>(8);
  const [gallons, setGallons] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const round = shape === "round";

  async function compute() {
    setErr(null);
    try {
      const body: Record<string, unknown> = {
        shape,
        length_ft: length ?? 0,
        width_ft: round ? (length ?? 0) : (width ?? 0),
        avg_depth_ft: useSlope ? ((shallow ?? 0) + (deep ?? 0)) / 2 : (avgDepth ?? 0),
      };
      if (useSlope) {
        body.shallow_depth_ft = shallow;
        body.deep_depth_ft = deep;
      }
      const r = await api.volume(body);
      setGallons(r.gallons);
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Pool Volume Estimator">
      <div className="space-y-3">
        <SelectField label="Shape" value={shape} onChange={setShape} options={shapes} />
        <div className="grid grid-cols-2 gap-3">
          <NumberField label={round ? "Diameter" : "Length"} unit="ft" value={length} onChange={setLength} />
          {!round && <NumberField label="Width" unit="ft" value={width} onChange={setWidth} />}
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input type="checkbox" checked={useSlope} onChange={(e) => setUseSlope(e.target.checked)} />
          Sloped floor (shallow → deep)
        </label>

        {useSlope ? (
          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Shallow depth" unit="ft" value={shallow} onChange={setShallow} />
            <NumberField label="Deep depth" unit="ft" value={deep} onChange={setDeep} />
          </div>
        ) : (
          <NumberField label="Average depth" unit="ft" value={avgDepth} onChange={setAvgDepth} />
        )}

        <ErrorText msg={err} />
        <Button variant="ghost" className="w-full" onClick={compute}>Calculate</Button>

        {gallons != null && (
          <div className="rounded-xl bg-sky-50 border border-sky-200 p-3 text-center">
            <div className="text-3xl font-bold text-sky-700">{gallons.toLocaleString()}</div>
            <div className="text-xs text-sky-600">US gallons (estimate)</div>
            <Button className="w-full mt-3" onClick={() => { onUse(gallons); onClose(); }}>
              Use this volume
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
