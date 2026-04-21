import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import type { ExperimentLogEntry, LogLevel } from "@/api/types";

interface Props {
  logs: ExperimentLogEntry[];
}

const LEVEL_STYLE: Record<LogLevel, { badge: string; text: string; bg: string }> = {
  debug: { badge: "bg-slate-100 text-slate-500", text: "text-slate-500", bg: "" },
  info: { badge: "bg-blue-100 text-blue-700", text: "text-slate-700", bg: "" },
  warning: { badge: "bg-amber-100 text-amber-700", text: "text-amber-800", bg: "bg-amber-50" },
  error: { badge: "bg-red-100 text-red-700", text: "text-red-800", bg: "bg-red-50" },
};

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return [
    d.getHours().toString().padStart(2, "0"),
    d.getMinutes().toString().padStart(2, "0"),
    d.getSeconds().toString().padStart(2, "0"),
  ].join(":");
}

export function ExperimentLog({ logs }: Props) {
  const { t } = useTranslation();
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (isNearBottom) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [logs.length]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          {t("experimentLog.title")}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-slate-300 font-mono" title={t("experimentLog.savedTo")}>
            💾 data/experiments.json
          </span>
          <span className="text-xs text-slate-400">{t("experimentLog.entryCount", { count: logs.length })}</span>
        </div>
      </div>

      <div
        ref={containerRef}
        className="h-56 overflow-y-auto p-3 font-mono text-xs"
        aria-live="polite"
        aria-label={t("experimentLog.ariaLabel")}
      >
        {logs.length === 0 ? (
          <p className="text-slate-400">{t("experimentLog.waitingForEntries")}</p>
        ) : (
          logs.map((entry) => {
            const style = LEVEL_STYLE[entry.level];
            return (
              <div
                key={entry.id}
                className={`flex gap-2 rounded px-1 py-0.5 leading-relaxed ${style.bg}`}
              >
                <span className="flex-shrink-0 text-slate-400">
                  {formatTimestamp(entry.timestamp)}
                </span>
                <span
                  className={`flex-shrink-0 rounded px-1 text-[10px] font-bold uppercase ${style.badge}`}
                >
                  {entry.level}
                </span>
                {entry.agent && (
                  <span className="flex-shrink-0 font-semibold text-violet-600">
                    [{entry.agent}]
                  </span>
                )}
                <span className={style.text}>{entry.message}</span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
