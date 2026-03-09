import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Overview" },
  { to: "/dashboard", label: "Live Dashboard" },
  { to: "/agents", label: "Agent Console" },
  { to: "/settings", label: "Settings" }
];

const UPCOMING_ITEMS = [
  "Experiments",
  "Context & Planning",
  "Diagnostics",
  "Tasks"
];

export function Sidebar() {
  return (
    <aside className="w-full border-b border-slate-200 bg-white/90 backdrop-blur md:w-72 md:border-b-0 md:border-r">
      <div className="p-5">
        <h1 className="text-lg font-bold text-slate-900">AutoHySeeker</h1>
        <p className="mt-1 text-sm text-slate-600">Web Control Panel</p>

        <nav className="mt-6 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-blue-600 text-white" : "text-slate-700 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-7 border-t border-slate-200 pt-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Upcoming
          </p>
          <ul className="mt-2 space-y-1">
            {UPCOMING_ITEMS.map((item) => (
              <li key={item} className="rounded-md px-3 py-2 text-sm text-slate-400">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}

