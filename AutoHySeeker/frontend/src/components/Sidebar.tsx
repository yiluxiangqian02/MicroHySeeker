import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FlaskConical } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "nav.overview" },
  { to: "/dashboard", label: "nav.dashboard" },
  { to: "/experiments", label: "nav.experiments" },
  { to: "/optimization", label: "nav.optimization" },
  { to: "/chat", label: "nav.chat" },
  { to: "/diagnostics", label: "nav.diagnostics" },
  { to: "/agents", label: "nav.agents" },
  { to: "/knowledge", label: "nav.knowledge" },
  { to: "/templates", label: "nav.templates" },
  { to: "/settings", label: "nav.settings" }
];

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const { t } = useTranslation();
  
  const handleNavClick = () => {
    // Close mobile menu when nav item is clicked
    if (onClose) {
      onClose();
    }
  };

  return (
    <aside className="w-full border-b border-slate-200 bg-white/90 backdrop-blur md:w-72 md:border-b-0 md:border-r h-full flex flex-col">
      <div className="p-5 flex-1 overflow-y-auto">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-sm flex-shrink-0">
            <FlaskConical className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-extrabold text-slate-900 tracking-tight truncate">AutoHySeeker</h1>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 truncate">AI EXPERIMENT MGR</p>
          </div>
        </div>

        <nav className="mt-8 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              onClick={handleNavClick}
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

