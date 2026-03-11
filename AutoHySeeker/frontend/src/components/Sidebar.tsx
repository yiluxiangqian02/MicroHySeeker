import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

const NAV_ITEMS = [
  { to: "/", label: "nav.overview" },
  { to: "/dashboard", label: "nav.dashboard" },
  { to: "/agents", label: "nav.agents" },
  { to: "/templates", label: "nav.templates" },
  { to: "/settings", label: "nav.settings" }
];

export function Sidebar() {
  const { t } = useTranslation();
  
  return (
    <aside className="w-full border-b border-slate-200 bg-white/90 backdrop-blur md:w-72 md:border-b-0 md:border-r">
      <div className="p-5">
        <h1 className="text-lg font-bold text-slate-900">AutoHySeeker</h1>
        <p className="mt-1 text-sm text-slate-600">AI 实验管家工作台</p>

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
              {t(item.label)}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}

