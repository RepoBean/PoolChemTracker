import { NavLink, Outlet } from "react-router-dom";
import { usePools } from "../state/PoolContext";

const tabs = [
  { to: "/", label: "Dashboard", icon: "🏠", end: true },
  { to: "/dosing", label: "Dosing", icon: "🧪" },
  { to: "/trends", label: "Trends", icon: "📈" },
  { to: "/consumption", label: "Usage & cost", icon: "📦" },
  { to: "/settings", label: "Setup", icon: "⚙️" },
];

export default function Layout() {
  const { current, pools, setCurrentId } = usePools();

  return (
    <div className="min-h-full md:flex">
      <aside className="bg-white border-b border-slate-200 md:border-b-0 md:border-r md:w-60 md:shrink-0 md:h-screen md:sticky md:top-0 flex md:flex-col">
        <div className="p-4 flex items-center gap-2 md:border-b md:border-slate-100">
          <span className="text-2xl">💧</span>
          <span className="font-bold text-lg">PoolMath</span>
        </div>

        <div className="hidden md:block px-4 py-3 border-b border-slate-100">
          {pools.length > 1 ? (
            <select
              value={current?.id ?? ""}
              onChange={(e) => setCurrentId(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            >
              {pools.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          ) : (
            <div className="text-sm text-slate-500">{current?.name ?? "No pool yet"}</div>
          )}
        </div>

        <nav className="flex md:flex-col md:p-2 ml-auto md:ml-0">
          {tabs.map((t) => (
            <NavLink
              key={t.to} to={t.to} end={t.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 md:rounded-xl text-sm font-medium transition ${
                  isActive ? "bg-sky-50 text-sky-700" : "text-slate-600 hover:bg-slate-50"
                }`
              }
            >
              <span className="text-lg leading-none">{t.icon}</span>
              <span className="hidden sm:inline">{t.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="flex-1 min-w-0 w-full">
        <div className="p-4 md:p-8 max-w-[1400px] mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
