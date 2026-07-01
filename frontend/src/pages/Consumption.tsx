import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import { usePools } from "../state/PoolContext";
import { NoPool } from "../components/Empty";
import { Button, Card, ErrorText, NumberField, TextField } from "../components/ui";
import { money, prettyUnit } from "../lib/format";
import type { Chemical, ConsumptionItem, DoseLog } from "../types";

export default function Consumption() {
  const { current } = usePools();
  const [items, setItems] = useState<ConsumptionItem[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [inv, setInv] = useState<Chemical[]>([]);
  const [doses, setDoses] = useState<DoseLog[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [unit, setUnit] = useState("fl_oz");
  const [qty, setQty] = useState<number | null>(null);
  const [cost, setCost] = useState<number | null>(null);

  async function load() {
    if (!current) return;
    const c = await api.consumption(current.id);
    setItems(c.items);
    setTotalCost(c.total_cost);
    setInv(await api.listChemicals(current.id));
    setDoses((await api.listDoses(current.id)).slice(-12).reverse());
  }

  useEffect(() => { load().catch(() => {}); }, [current]);

  if (!current) return <NoPool />;

  async function addChem() {
    setErr(null);
    try {
      await api.createChemical(current!.id, { name, unit, qty_on_hand: qty ?? 0, cost_per_unit: cost });
      setName(""); setQty(null); setCost(null);
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function del(id: number) {
    await api.deleteChemical(current!.id, id);
    await load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Chemical usage &amp; cost</h1>

      <div className="grid lg:grid-cols-2 gap-6 items-start">
        {/* Left: spend, breakdown, history */}
        <div className="space-y-6">
          <Card>
            <div className="flex items-baseline justify-between">
              <span className="text-sm text-slate-500">Total spend (logged doses)</span>
              <span className="text-3xl font-bold">${totalCost.toFixed(2)}</span>
            </div>
            {items.length > 0 && (
              <div className="mt-3">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={items} margin={{ top: 5, right: 8, left: -20, bottom: 0 }}>
                    <XAxis dataKey="chemical" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="total_cost" fill="#0284c7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>

          {items.length > 0 && (
            <Card>
              <div className="text-sm font-medium mb-2">By chemical</div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-slate-400 text-left">
                    <th className="font-normal">Chemical</th><th className="font-normal">Used</th>
                    <th className="font-normal">Cost</th><th className="font-normal">#</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((i) => (
                    <tr key={i.chemical} className="border-t border-slate-100">
                      <td className="py-1">{i.chemical}</td>
                      <td>{i.total_amount} {prettyUnit(i.unit)}</td>
                      <td>{money(i.total_cost)}</td>
                      <td>{i.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}

          {doses.length > 0 && (
            <Card>
              <div className="text-sm font-medium mb-2">Recent doses</div>
              <div className="space-y-1 text-sm">
                {doses.map((d) => (
                  <div key={d.id} className="flex justify-between border-t border-slate-100 py-1">
                    <span>{d.chemical}</span>
                    <span className="text-slate-500">
                      {d.amount} {prettyUnit(d.unit)}{d.cost != null ? ` · ${money(d.cost)}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right: inventory */}
        <div className="space-y-6">
          <Card className="space-y-3">
            <div className="text-sm font-medium">Inventory</div>
            {inv.length === 0 && <p className="text-sm text-slate-400">No chemicals tracked yet.</p>}
            {inv.map((c) => (
              <div key={c.id} className="flex items-center justify-between text-sm border-t border-slate-100 pt-2">
                <div>
                  <div className="font-medium">{c.name}</div>
                  <div className="text-slate-400">
                    {c.qty_on_hand} {prettyUnit(c.unit)}
                    {c.cost_per_unit != null ? ` · ${money(c.cost_per_unit)}/${prettyUnit(c.unit)}` : ""}
                  </div>
                </div>
                <button onClick={() => del(c.id)} className="text-red-500 text-sm">Remove</button>
              </div>
            ))}
            <div className="grid grid-cols-2 gap-2 pt-2">
              <TextField label="Name" value={name} onChange={setName} placeholder="12.5% liquid chlorine" />
              <TextField label="Unit" value={unit} onChange={setUnit} />
              <NumberField label="Qty on hand" value={qty} onChange={setQty} />
              <NumberField label="$ / unit" value={cost} step="0.01" onChange={setCost} />
            </div>
            <ErrorText msg={err} />
            <Button variant="ghost" className="w-full" onClick={addChem} disabled={!name}>Add chemical</Button>
          </Card>
        </div>
      </div>
    </div>
  );
}
