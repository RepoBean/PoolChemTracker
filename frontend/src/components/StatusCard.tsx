import { Card } from "./ui";
import { dotClasses, statusClasses } from "../lib/status";
import type { Status } from "../lib/status";

export function StatusCard({
  label, value, unit, status, sub,
}: {
  label: string;
  value: number | string | null | undefined;
  unit?: string;
  status: Status;
  sub?: string;
}) {
  return (
    <Card className={`border ${statusClasses(status)}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
        <span className={`h-2.5 w-2.5 rounded-full ${dotClasses(status)}`} />
      </div>
      <div className="mt-1 text-3xl font-bold tracking-tight">
        {value ?? "—"}
        {unit ? <span className="text-base font-normal ml-1 opacity-70">{unit}</span> : null}
      </div>
      {sub ? <div className="text-xs mt-1 opacity-80">{sub}</div> : null}
    </Card>
  );
}
