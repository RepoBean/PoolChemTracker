import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { StatusCard } from "../components/StatusCard";
import { NoPool } from "../components/Empty";
import { Button, Card } from "../components/ui";
import { csiStatus, fcStatus, phStatus } from "../lib/status";
import type { PoolDetail } from "../types";

function Reading({ label, v, unit }: { label: string; v: number | null | undefined; unit?: string }) {
  return (
    <div>
      <div className="text-slate-400 text-xs">{label}</div>
      <div className="font-medium">{v ?? "—"}{v != null && unit ? ` ${unit}` : ""}</div>
    </div>
  );
}

export default function Dashboard() {
  const { current, loading } = usePools();
  const [detail, setDetail] = useState<PoolDetail | null>(null);
  const [rec, setRec] = useState<string | null>(null);

  useEffect(() => {
    if (!current) return;
    let alive = true;
    setDetail(null);
    setRec(null);
    api.poolDetail(current.id).then(async (d) => {
      if (!alive) return;
      setDetail(d);
      const t = d.latest_test;
      const tg = d.targets;
      if (t?.fc != null && tg && t.fc < tg.target_fc_low) {
        const goal = (tg.target_fc_low + tg.target_fc_high) / 2;
        try {
          const dose = await api.dose({
            parameter: "fc", chemical: "liquid_chlorine", current: t.fc, goal,
            volume_gal: d.pool.volume_gal, strength: "12.5",
          });
          if (alive) setRec(`Add ~${dose.amount} ${dose.unit} of 12.5% liquid chlorine to reach FC ${goal.toFixed(1)}.`);
        } catch { /* ignore */ }
      } else if (t?.fc != null && tg) {
        setRec(`FC ${t.fc} is in the target range (${tg.target_fc_low}–${tg.target_fc_high}). 👍`);
      }
    }).catch(() => {});
    return () => { alive = false; };
  }, [current]);

  if (loading) return <div className="text-slate-500">Loading…</div>;
  if (!current) return <NoPool />;

  const t = detail?.latest_test ?? null;
  const tg = detail?.targets ?? null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{current.name}</h1>
          <p className="text-sm text-slate-500">
            {t ? `Last tested ${new Date(t.taken_at).toLocaleString()}` : "No tests yet"}
          </p>
        </div>
        <Link to="/log"><Button>+ Log</Button></Link>
      </div>

      {!t ? (
        <Card>Log your first test to see targets and status.</Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <StatusCard label="Free Chlorine" value={t.fc} unit="ppm" status={fcStatus(t.fc, tg)}
              sub={tg ? `target ${tg.target_fc_low}–${tg.target_fc_high} · min ${tg.min_fc} · SLAM ${tg.slam_fc}` : "enter CYA for targets"} />
            <StatusCard label="pH" value={t.ph} status={phStatus(t.ph)} sub="ideal 7.6–7.8" />
            <StatusCard label="CSI" value={t.csi} status={csiStatus(detail?.csi_status)}
              sub={detail?.csi_status ?? "needs pH, temp, CH, TA"} />
            <StatusCard label="CC" value={t.cc} unit="ppm"
              status={t.cc != null ? (t.cc > 0.5 ? "low" : "ideal") : "unknown"} sub="keep ≤ 0.5" />
          </div>

          {rec && (
            <Card className="border-sky-200 bg-sky-50">
              <div className="text-sm font-medium text-sky-800">Next action</div>
              <div className="text-sky-900 mt-1">{rec}</div>
              <Link to="/dosing"><Button variant="ghost" className="mt-3">Open dosing →</Button></Link>
            </Card>
          )}

          <Card>
            <div className="text-sm font-medium mb-3">Latest readings</div>
            <div className="grid grid-cols-3 gap-y-3 text-sm">
              <Reading label="TA" v={t.ta} />
              <Reading label="CH" v={t.ch} />
              <Reading label="CYA" v={t.cya} />
              <Reading label="Salt" v={t.salt} />
              <Reading label="Temp" v={t.water_temp_f} unit="°F" />
              <Reading label="CSI" v={t.csi} />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
