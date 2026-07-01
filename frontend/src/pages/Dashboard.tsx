import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid, Line, LineChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { StatusCard } from "../components/StatusCard";
import { TestForm } from "../components/TestForm";
import { NoPool } from "../components/Empty";
import { Button, Card } from "../components/ui";
import { bandStatus, csiStatus, dotClasses, fcStatus, phStatus } from "../lib/status";
import type { Status } from "../lib/status";
import type { Pool, PoolDetail, TestLog } from "../types";

const CH_RANGE: Record<string, [number, number, number, number]> = {
  plaster: [250, 350, 550, 650], pebble: [250, 350, 550, 650], painted: [250, 350, 550, 650],
  vinyl: [0, 0, 999, 650], fiberglass: [0, 0, 999, 650],
};

function readingStatus(param: string, v: number | null | undefined, pool: Pool): Status {
  if (v == null) return "unknown";
  if (param === "ta") return bandStatus(v, 50, 60, 80, 90);
  if (param === "ch") {
    const r = CH_RANGE[pool.surface_type] ?? CH_RANGE.plaster;
    return bandStatus(v, r[0], r[1], r[2], r[3]);
  }
  if (param === "cya") {
    return pool.chlorine_source === "swg" ? bandStatus(v, 60, 60, 90, 90) : bandStatus(v, 30, 40, 50, 60);
  }
  return "unknown";
}

function Reading({ label, v, status }: { label: string; v: number | null | undefined; status: Status }) {
  return (
    <div>
      <div className="text-slate-400 text-xs flex items-center gap-1">
        <span className={`h-1.5 w-1.5 rounded-full ${dotClasses(status)}`} />{label}
      </div>
      <div className="font-semibold text-lg">{v ?? "—"}</div>
    </div>
  );
}

function Th({ children }: { children: ReactNode }) {
  return <th className="font-normal pr-3 pb-1">{children}</th>;
}
function Td({ v }: { v: number | null | undefined }) {
  return <td className="pr-3 py-1.5">{v ?? "—"}</td>;
}

function MiniChart({
  title, data, dataKey, color, band, domain,
}: {
  title: string; data: Record<string, unknown>[]; dataKey: string; color: string;
  band?: [number, number]; domain?: [number, number];
}) {
  return (
    <div>
      <div className="text-xs text-slate-500 mb-1">{title}</div>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="t" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} width={26} domain={domain ?? ["auto", "auto"]} />
          <Tooltip />
          {band && <ReferenceArea y1={band[0]} y2={band[1]} fill="#22c55e" fillOpacity={0.12} />}
          <Line type="monotone" dataKey={dataKey} stroke={color} dot={false} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Dashboard() {
  const { current, loading } = usePools();
  const [detail, setDetail] = useState<PoolDetail | null>(null);
  const [tests, setTests] = useState<TestLog[]>([]);
  const [rec, setRec] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!current) return;
    const [d, ts] = await Promise.all([api.poolDetail(current.id), api.listTests(current.id)]);
    setDetail(d);
    setTests(ts);
    const t = d.latest_test;
    const tg = d.targets;
    if (t?.fc != null && tg && t.fc < tg.target_fc_low) {
      const goal = (tg.target_fc_low + tg.target_fc_high) / 2;
      try {
        const dose = await api.dose({
          parameter: "fc", chemical: "liquid_chlorine", current: t.fc, goal,
          volume_gal: d.pool.volume_gal, strength: "12.5",
        });
        setRec(`Add ~${dose.amount} ${dose.unit} of 12.5% liquid chlorine → FC ${goal.toFixed(1)}`);
      } catch { setRec(null); }
    } else if (t?.fc != null && tg) {
      setRec(`FC ${t.fc} is in range (${tg.target_fc_low}–${tg.target_fc_high}) 👍`);
    } else {
      setRec(null);
    }
  }, [current]);

  useEffect(() => {
    setDetail(null);
    setTests([]);
    setRec(null);
    reload().catch(() => {});
  }, [reload]);

  if (loading) return <div className="text-slate-500">Loading…</div>;
  if (!current) return <NoPool />;

  const t = detail?.latest_test ?? null;
  const tg = detail?.targets ?? null;
  const chart = tests.map((x) => ({
    t: new Date(x.taken_at).toLocaleDateString(undefined, { month: "numeric", day: "numeric" }),
    fc: x.fc ?? undefined, ph: x.ph ?? undefined, csi: x.csi ?? undefined,
  }));
  const recent = [...tests].reverse().slice(0, 8);
  const srcLabel =
    current.chlorine_source === "swg" ? "SWG" : current.chlorine_source === "tabs" ? "tabs" : "liquid chlorine";

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">{current.name}</h1>
          <p className="text-sm text-slate-500">
            {t ? `Last tested ${new Date(t.taken_at).toLocaleString()}` : "No tests yet"}
          </p>
        </div>
        <div className="text-sm text-slate-500">
          {current.volume_gal.toLocaleString()} gal · {current.surface_type} · {srcLabel}
        </div>
      </header>

      {t && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatusCard label="Free Chlorine" value={t.fc} unit="ppm" status={fcStatus(t.fc, tg)}
            sub={tg ? `target ${tg.target_fc_low}–${tg.target_fc_high} · min ${tg.min_fc} · SLAM ${tg.slam_fc}` : "enter CYA for targets"} />
          <StatusCard label="pH" value={t.ph} status={phStatus(t.ph)} sub="ideal 7.6–7.8" />
          <StatusCard label="CSI" value={t.csi} status={csiStatus(detail?.csi_status)}
            sub={detail?.csi_status ?? "needs pH, temp, CH, TA"} />
          <StatusCard label="CC" value={t.cc} unit="ppm"
            status={t.cc != null ? (t.cc > 0.5 ? "low" : "ideal") : "unknown"} sub="keep ≤ 0.5" />
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left: readings, trends, recent tests */}
        <div className="xl:col-span-8 space-y-6">
          {t && (
            <Card>
              <div className="text-sm font-medium mb-3">Latest readings</div>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-y-4 gap-x-2">
                <Reading label="TA" v={t.ta} status={readingStatus("ta", t.ta, current)} />
                <Reading label="CH" v={t.ch} status={readingStatus("ch", t.ch, current)} />
                <Reading label="CYA" v={t.cya} status={readingStatus("cya", t.cya, current)} />
                <Reading label="Salt" v={t.salt} status="unknown" />
                <Reading label="Temp °F" v={t.water_temp_f} status="unknown" />
                <Reading label="CSI" v={t.csi} status={csiStatus(detail?.csi_status)} />
              </div>
            </Card>
          )}

          {chart.length > 0 && (
            <Card>
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium">Trends</div>
                <Link to="/trends" className="text-sky-600 text-sm">See all →</Link>
              </div>
              <div className="grid sm:grid-cols-3 gap-4">
                <MiniChart title="FC" data={chart} dataKey="fc" color="#0284c7"
                  band={tg ? [tg.target_fc_low, tg.target_fc_high] : undefined} />
                <MiniChart title="pH" data={chart} dataKey="ph" color="#7c3aed" band={[7.6, 7.8]} domain={[6.8, 8.2]} />
                <MiniChart title="CSI" data={chart} dataKey="csi" color="#059669" band={[-0.3, 0.3]} domain={[-1, 1]} />
              </div>
            </Card>
          )}

          {recent.length > 0 && (
            <Card>
              <div className="text-sm font-medium mb-2">Recent tests</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-slate-400 text-left">
                      <Th>Date</Th><Th>FC</Th><Th>pH</Th><Th>TA</Th><Th>CH</Th><Th>CYA</Th><Th>CSI</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((r) => (
                      <tr key={r.id} className="border-t border-slate-100">
                        <td className="pr-3 py-1.5">{new Date(r.taken_at).toLocaleDateString()}</td>
                        <Td v={r.fc} /><Td v={r.ph} /><Td v={r.ta} /><Td v={r.ch} /><Td v={r.cya} /><Td v={r.csi} />
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {!t && (
            <Card>Log your first test using the form on the right — targets and status will appear here.</Card>
          )}
        </div>

        {/* Right rail: log form, targets, next action */}
        <div className="xl:col-span-4 space-y-6">
          <Card>
            <div className="text-sm font-medium mb-3">Log a test</div>
            <TestForm onSaved={reload} />
          </Card>

          {tg && (
            <Card>
              <div className="text-sm font-medium mb-2">Targets (CYA {tg.cya})</div>
              <ul className="text-sm space-y-1 text-slate-600">
                <li>FC target <b>{tg.target_fc_low}–{tg.target_fc_high}</b> ppm</li>
                <li>FC minimum <b>{tg.min_fc}</b> · SLAM <b>{tg.slam_fc}</b></li>
                <li>Mustard-algae SLAM <b>{tg.mustard_slam_fc}</b></li>
                <li className={tg.cya_in_recommended_range ? "text-green-600" : "text-amber-600"}>
                  CYA recommended {tg.recommended_cya_low}–{tg.recommended_cya_high} {tg.cya_in_recommended_range ? "✓" : "⚠"}
                </li>
              </ul>
            </Card>
          )}

          {rec && (
            <Card className="border-sky-200 bg-sky-50">
              <div className="text-sm font-medium text-sky-800">Next action</div>
              <div className="text-sky-900 mt-1 text-sm">{rec}</div>
              <Link to="/dosing"><Button variant="ghost" className="mt-3 w-full">Open dosing →</Button></Link>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
