import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl bg-white shadow-sm border border-slate-200 p-4 ${className}`}>
      {children}
    </div>
  );
}

type BtnProps = {
  children: ReactNode;
  variant?: "primary" | "ghost" | "danger";
  className?: string;
  type?: "button" | "submit";
  onClick?: () => void;
  disabled?: boolean;
};

export function Button({ children, variant = "primary", className = "", ...p }: BtnProps) {
  const base =
    "rounded-xl px-4 py-2.5 font-medium transition active:scale-[.98] disabled:opacity-50 disabled:pointer-events-none";
  const styles: Record<string, string> = {
    primary: "bg-sky-600 text-white hover:bg-sky-700",
    ghost: "bg-slate-100 text-slate-700 hover:bg-slate-200",
    danger: "bg-red-100 text-red-700 hover:bg-red-200",
  };
  return (
    <button className={`${base} ${styles[variant]} ${className}`} {...p}>
      {children}
    </button>
  );
}

function fieldWrap(label: string, unit: string | undefined, child: ReactNode) {
  return (
    <label className="block">
      <span className="text-sm text-slate-600">
        {label}
        {unit ? <span className="text-slate-400"> ({unit})</span> : null}
      </span>
      {child}
    </label>
  );
}

const inputCls =
  "mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500";

export function NumberField({
  label, unit, value, onChange, step = "0.1", placeholder, min,
}: {
  label: string; unit?: string; value: number | null; step?: string; placeholder?: string;
  min?: number;
  onChange: (v: number | null) => void;
}) {
  return fieldWrap(
    label, unit,
    <input
      type="number" inputMode="decimal" step={step} placeholder={placeholder} min={min}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      className={inputCls}
    />,
  );
}

export function TextField({
  label, value, onChange, placeholder,
}: {
  label: string; value: string; placeholder?: string; onChange: (v: string) => void;
}) {
  return fieldWrap(
    label, undefined,
    <input value={value} placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)} className={inputCls} />,
  );
}

export function SelectField({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return fieldWrap(
    label, undefined,
    <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>,
  );
}

export function Toggle({
  label, checked, onChange,
}: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between py-2">
      <span className="text-sm text-slate-700">{label}</span>
      <button
        type="button" role="switch" aria-checked={checked} aria-label={label}
        onClick={() => onChange(!checked)}
        className={`h-6 w-11 rounded-full transition ${checked ? "bg-sky-600" : "bg-slate-300"}`}
      >
        <span className={`block h-5 w-5 rounded-full bg-white transition ${checked ? "translate-x-5" : "translate-x-1"}`} />
      </button>
    </label>
  );
}

export function Modal({
  open, onClose, title, children,
}: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4"
         onClick={onClose}>
      <div className="w-full sm:max-w-md rounded-t-3xl sm:rounded-2xl bg-white p-5 max-h-[90vh] overflow-auto"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close"
                  className="text-slate-400 text-2xl leading-none">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function ErrorText({ msg }: { msg: string | null }) {
  if (!msg) return null;
  return <div className="rounded-xl bg-red-50 text-red-700 border border-red-200 px-3 py-2 text-sm">{msg}</div>;
}
