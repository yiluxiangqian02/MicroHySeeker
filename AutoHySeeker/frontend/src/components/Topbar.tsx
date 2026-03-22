import { useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSettingsStore } from "@/stores/settingsStore";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Breadcrumb } from "@/components/Breadcrumb";
import { Menu } from "lucide-react";

const ROUTE_TITLE_MAP: Record<string, string> = {
  "/": "nav.overview",
  "/dashboard": "nav.dashboard",
  "/agents": "nav.agents",
  "/settings": "nav.settings"
};

interface TopbarProps {
  onMenuToggle?: () => void;
}

export function Topbar({ onMenuToggle }: TopbarProps) {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const apiBaseUrl = useSettingsStore((state) => state.apiBaseUrl);

  const title = useMemo(() => {
    const key = ROUTE_TITLE_MAP[pathname] ?? "AutoHySeeker";
    return key.includes('.') ? t(key) : key;
  }, [pathname, t]);

  return (
    <header className="border-b border-slate-200 bg-white/80 px-5 py-4 backdrop-blur">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={onMenuToggle}
              className="md:hidden p-2 hover:bg-slate-100 rounded-lg transition"
              aria-label="Toggle menu"
            >
              <Menu className="h-5 w-5 text-slate-600" />
            </button>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
              <Breadcrumb />
            </div>
          </div>
          <LanguageSwitcher />
        </div>
        <div className="text-sm text-slate-500">
          API Base URL: <code className="rounded bg-slate-100 px-1.5 py-0.5">{apiBaseUrl}</code>
        </div>
      </div>
    </header>
  );
}
