export type ChlorineSource = "liquid" | "swg" | "tabs";
export type Surface = "plaster" | "pebble" | "vinyl" | "fiberglass" | "painted";

export interface Pool {
  id: number;
  name: string;
  volume_gal: number;
  surface_type: Surface;
  chlorine_source: ChlorineSource;
  uses_salt: boolean;
  uses_borates: boolean;
  created_at: string;
}

export interface TestLog {
  id: number;
  pool_id: number;
  taken_at: string;
  fc?: number | null;
  cc?: number | null;
  ph?: number | null;
  ta?: number | null;
  ch?: number | null;
  cya?: number | null;
  salt?: number | null;
  borate?: number | null;
  water_temp_f?: number | null;
  tds?: number | null;
  csi?: number | null;
  notes?: string | null;
}

export interface Targets {
  cya: number;
  source: string;
  min_fc: number;
  target_fc_low: number;
  target_fc_high: number;
  slam_fc: number;
  mustard_slam_fc: number;
  recommended_cya_low: number;
  recommended_cya_high: number;
  cya_in_recommended_range: boolean;
}

export interface DoseResult {
  chemical: string;
  parameter: string;
  amount: number;
  unit: string;
  direction: string;
  side_effects: Record<string, number>;
  note: string;
}

export interface Recommendation {
  level: "ok" | "info" | "warn" | "danger";
  message: string;
  dose?: DoseResult;
}

export interface PoolDetail {
  pool: Pool;
  latest_test: TestLog | null;
  targets: Targets | null;
  csi_status: string | null;
}

export interface LogTestResult {
  test: TestLog;
  targets: Targets | null;
  csi_status: string | null;
  recommendation: Recommendation | null;
}

export interface Chemical {
  id: number;
  pool_id: number;
  name: string;
  strength?: string | null;
  unit: string;
  qty_on_hand: number;
  cost_per_unit?: number | null;
}

export interface DoseLog {
  id: number;
  chemical: string;
  amount: number;
  unit: string;
  cost?: number | null;
  applied_at: string;
  parameter_targeted?: string | null;
}

export interface ConsumptionItem {
  chemical: string;
  unit: string;
  total_amount: number;
  total_cost: number;
  count: number;
}
