import { useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useSettingsStore } from "@/stores/settingsStore";

const ROUTE_TITLE_MAP: Record<string, string> = {
  "/": "Overview",
  "/settings": "Settings"
};

export function Topbar() {
  const { pathname } = useLocation();
  const apiBaseUrl = useSettingsStore((state) => state.apiBaseUrl);

  const title = useMemo(() => ROUTE_TITLE_MAP[pathname] ?? "AutoHySeeker", [pathname]);

  return (
    <header className="border-b border-slate-200 bg-white/80 px-5 py-4 backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
          <p className="mt-1 text-sm text-slate-500">
            API Base URL: <code className="rounded bg-slate-100 px-1.5 py-0.5">{apiBaseUrl}</code>
          </p>
        </div>
      </div>
    </header>
  );
}

