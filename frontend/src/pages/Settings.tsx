import { useEffect, useState } from "react";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { Button, Card, ErrorText, NumberField, SelectField, TextField, Toggle } from "../components/ui";
import { VolumeEstimator } from "../components/VolumeEstimator";

const surfaces = [
  { value: "plaster", label: "Plaster / Gunite" },
  { value: "pebble", label: "Pebble" },
  { value: "vinyl", label: "Vinyl" },
  { value: "fiberglass", label: "Fiberglass" },
  { value: "painted", label: "Painted" },
];
const sources = [
  { value: "liquid", label: "Liquid chlorine" },
  { value: "swg", label: "Salt water generator" },
  { value: "tabs", label: "Tabs (trichlor)" },
];

export default function Settings() {
  const { current, refresh } = usePools();
  const [name, setName] = useState("");
  const [volume, setVolume] = useState<number | null>(null);
  const [surface, setSurface] = useState("plaster");
  const [source, setSource] = useState("liquid");
  const [salt, setSalt] = useState(false);
  const [borates, setBorates] = useState(false);
  const [estOpen, setEstOpen] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (current) {
      setName(current.name);
      setVolume(current.volume_gal);
      setSurface(current.surface_type);
      setSource(current.chlorine_source);
      setSalt(current.uses_salt);
      setBorates(current.uses_borates);
    }
  }, [current]);

  async function save() {
    setErr(null);
    setSaved(false);
    try {
      const body = {
        name, volume_gal: volume ?? 0, surface_type: surface,
        chlorine_source: source, uses_salt: salt, uses_borates: borates,
      };
      if (current) await api.updatePool(current.id, body as never);
      else await api.createPool(body as never);
      await refresh();
      setSaved(true);
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">{current ? "Pool settings" : "Set up your pool"}</h1>
      <Card className="space-y-3">
        <TextField label="Pool name" value={name} onChange={setName} placeholder="Backyard" />
        <div>
          <NumberField label="Volume" unit="gal" step="100" value={volume} onChange={setVolume} />
          <button onClick={() => setEstOpen(true)} className="text-sky-600 text-sm mt-1">📐 Estimate volume</button>
        </div>
        <SelectField label="Surface" value={surface} onChange={setSurface} options={surfaces} />
        <SelectField label="Chlorine source" value={source} onChange={setSource} options={sources} />
        <Toggle label="Salt pool" checked={salt} onChange={setSalt} />
        <Toggle label="Uses borates" checked={borates} onChange={setBorates} />
        <ErrorText msg={err} />
        {saved && <div className="text-green-600 text-sm">Saved ✓</div>}
        <Button className="w-full" onClick={save} disabled={!name || !volume}>
          {current ? "Save changes" : "Create pool"}
        </Button>
      </Card>

      <p className="text-xs text-slate-400">
        Follows TroubleFreePool methodology; chemistry validated against TFP's published tables.
        Always confirm a dose with your own test kit before adding it.
      </p>

      <VolumeEstimator open={estOpen} onClose={() => setEstOpen(false)} onUse={(g) => setVolume(g)} />
    </div>
  );
}
