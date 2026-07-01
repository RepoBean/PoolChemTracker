import type {
  Chemical, ConsumptionItem, DoseLog, DoseResult, LogTestResult, Pool, PoolDetail,
  Targets, TestLog,
} from "./types";

const BASE = "/api";

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listPools: () => req<Pool[]>("/pools"),
  createPool: (b: Partial<Pool>) => req<Pool>("/pools", { method: "POST", body: JSON.stringify(b) }),
  updatePool: (id: number, b: Partial<Pool>) =>
    req<Pool>(`/pools/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
  poolDetail: (id: number) => req<PoolDetail>(`/pools/${id}`),

  logTest: (id: number, b: Record<string, unknown>) =>
    req<LogTestResult>(`/pools/${id}/tests`, { method: "POST", body: JSON.stringify(b) }),
  listTests: (id: number) => req<TestLog[]>(`/pools/${id}/tests`),

  targets: (cya: number, source: string) =>
    req<Targets>("/chem/targets", { method: "POST", body: JSON.stringify({ cya, chlorine_source: source }) }),
  dose: (b: Record<string, unknown>) =>
    req<DoseResult>("/chem/dose", { method: "POST", body: JSON.stringify(b) }),
  csi: (b: Record<string, unknown>) =>
    req<{ csi: number; status: string }>("/chem/csi", { method: "POST", body: JSON.stringify(b) }),
  volume: (b: Record<string, unknown>) =>
    req<{ gallons: number }>("/chem/volume", { method: "POST", body: JSON.stringify(b) }),

  listChemicals: (id: number) => req<Chemical[]>(`/pools/${id}/chemicals`),
  createChemical: (id: number, b: Record<string, unknown>) =>
    req<Chemical>(`/pools/${id}/chemicals`, { method: "POST", body: JSON.stringify(b) }),
  deleteChemical: (id: number, cid: number) =>
    req<void>(`/pools/${id}/chemicals/${cid}`, { method: "DELETE" }),

  logDose: (id: number, b: Record<string, unknown>) =>
    req<DoseLog>(`/pools/${id}/doses`, { method: "POST", body: JSON.stringify(b) }),
  listDoses: (id: number) => req<DoseLog[]>(`/pools/${id}/doses`),
  consumption: (id: number) =>
    req<{ items: ConsumptionItem[]; total_cost: number }>(`/pools/${id}/consumption`),
};
