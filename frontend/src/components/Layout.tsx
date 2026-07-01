import { NavLink, Outlet } from "react-router-dom";
import { usePools } from "../state/PoolContext";

const tabs = [
  { to: "/", label: "Home", icon: "🏠", end: true },
  { to: "/log", label: "Log", icon: "📝" },
  { to: "/dosing", label: "Dose", icon: "🧪" },
  { to: "/trends", label: "Trends", icon: "📈" },
  { to: "/consumption", label: "Usage", icon: "📦" },
  { to: "/settings", label: "Setup", icon: "⚙️" },
];

export default function Layout() {
  const { current, pools, setCurrentId } = usePools();

  return (
    <div className="min-h-full flex flex-col">
      <header className="sticky top-0 z-10 bg-sky-600 text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">💧</span>
          <span className="font-semibold">PoolMath</span>
        </div>
        {pools.length > 1 ? (
          <select
            value={current?.id ?? ""}
            onChange={(e) => setCurrentId(Number(e.target.value))}
            className="bg-sky-500 text-white rounded-lg px-2 py-1 text-sm"
          >
            {pools.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        ) : (
          <span className="text-sm text-sky-100">{current?.name ?? ""}</span>
        )}
      </header>

      <main className="flex-1 p-4 pb-24 max-w-2xl w-full mx-auto">
        <Outlet />
      </main>

      <nav className="fixed bottom-0 inset-x-0 bg-white border-t border-slate-200 grid grid-cols-6">
        {tabs.map((t) => (
          <NavLink
            key={t.to} to={t.to} end={t.end}
            className={({ isActive }) =>
              `flex flex-col items-center py-2 text-[11px] ${isActive ? "text-sky-600" : "text-slate-500"}`
            }
          >
            <span className="text-lg leading-none">{t.icon}</span>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
