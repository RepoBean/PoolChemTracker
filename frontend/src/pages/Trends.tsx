import { useEffect, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { NoPool } from "../components/Empty";
import { Card } from "../components/ui";
import type { Targets, TestLog } from "../types";

const RANGES = [
  { d: 7, label: "7d" }, { d: 30, label: "30d" }, { d: 90, label: "90d" }, { d: 0, label: "All" },
];

interface Band { y1: number; y2: number }

function ChartCard({
  title, data, dataKey, color, band, domain, multi,
}: {
  title: string;
  data: Record<string, unknown>[];
  dataKey?: string;
  color?: string;
  band?: Band;
  domain?: [number, number];
  multi?: boolean;
}) {
  return (
    <Card>
      <div className="text-sm font-medium mb-2">{title}</div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="t" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} domain={domain ?? ["auto", "auto"]} />
          <Tooltip />
          {band && <ReferenceArea y1={band.y1} y2={band.y2} fill="#22c55e" fillOpacity={0.12} />}
          {multi ? (
            <>
              <Line type="monotone" dataKey="ta" stroke="#f59e0b" dot={false} name="TA" connectNulls />
              <Line type="monotone" dataKey="ch" stroke="#0ea5e9" dot={false} name="CH" connectNulls />
              <Line type="monotone" dataKey="cya" stroke="#a855f7" dot={false} name="CYA" connectNulls />
            </>
          ) : (
            <Line type="monotone" dataKey={dataKey} stroke={color} dot={{ r: 2 }} connectNulls />
          )}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

export default function Trends() {
  const { current } = usePools();
  const [tests, setTests] = useState<TestLog[]>([]);
  const [targets, setTargets] = useState<Targets | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    if (!current) return;
    api.listTests(current.id).then(async (ts) => {
      setTests(ts);
      const last = [...ts].reverse().find((t) => t.cya != null);
      if (last?.cya != null) {
        try {
          setTargets(await api.targets(last.cya, current.chlorine_source));
        } catch { /* ignore */ }
      }
    }).catch(() => {});
  }, [current]);

  if (!current) return <NoPool />;

  const cutoff = days ? Date.now() - days * 86400000 : 0;
  const data = tests
    .filter((t) => new Date(t.taken_at).getTime() >= cutoff)
    .map((t) => ({
      t: new Date(t.taken_at).toLocaleDateString(undefined, { month: "numeric", day: "numeric" }),
      fc: t.fc ?? undefined, ph: t.ph ?? undefined, csi: t.csi ?? undefined,
      ta: t.ta ?? undefined, ch: t.ch ?? undefined, cya: t.cya ?? undefined,
    }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Trends</h1>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button key={r.label} onClick={() => setDays(r.d)}
              className={`px-3 py-1 rounded-lg text-sm ${days === r.d ? "bg-sky-600 text-white" : "bg-slate-200 text-slate-600"}`}>
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {data.length === 0 ? (
        <Card>No tests in this range.</Card>
      ) : (
        <>
          <ChartCard title="Free Chlorine (ppm)" data={data} dataKey="fc" color="#0284c7"
            band={targets ? { y1: targets.target_fc_low, y2: targets.target_fc_high } : undefined} />
          <ChartCard title="pH" data={data} dataKey="ph" color="#7c3aed" band={{ y1: 7.6, y2: 7.8 }} domain={[6.8, 8.2]} />
          <ChartCard title="CSI" data={data} dataKey="csi" color="#059669" band={{ y1: -0.3, y2: 0.3 }} domain={[-1, 1]} />
          <ChartCard title="TA / CH / CYA (ppm)" data={data} multi />
        </>
      )}
    </div>
  );
}
