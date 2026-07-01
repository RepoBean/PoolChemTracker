import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api";
import type { Pool } from "../types";

interface PoolCtx {
  pools: Pool[];
  current: Pool | null;
  currentId: number | null;
  setCurrentId: (id: number) => void;
  refresh: () => Promise<void>;
  loading: boolean;
}

const Ctx = createContext<PoolCtx | undefined>(undefined);

export function PoolProvider({ children }: { children: ReactNode }) {
  const [pools, setPools] = useState<Pool[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const p = await api.listPools();
    setPools(p);
    setCurrentId((cur) => cur ?? p[0]?.id ?? null);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh().catch(() => setLoading(false));
  }, [refresh]);

  const current = pools.find((p) => p.id === currentId) ?? null;

  return (
    <Ctx.Provider value={{ pools, current, currentId, setCurrentId, refresh, loading }}>
      {children}
    </Ctx.Provider>
  );
}

export function usePools(): PoolCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("usePools must be used within PoolProvider");
  return v;
}
