import { Link } from "react-router-dom";
import { ArrowRight, Loader2, RefreshCw, Play, Square } from "lucide-react";
import { useTranslation } from "react-i18next";

export interface OptimizationLoopStatus {
  status: "idle" | "running" | "paused" | "completed" | "error" | "stopped" | "blocked" | "starting" | "stopping" | "executing" | "designing" | "evaluating" | "analyzing";
  currentIteration?: number;
  maxIterations?: number;
  bestYield?: number;
  activeExperiment?: string;
  projectName?: string;
  onStart?: () => void;
  onStop?: () => void;
  isActionLoading?: boolean;
}

export function OptimizationStatusCard({
  status = "idle",
  currentIteration = 0,
  maxIterations = 10,
  bestYield,
  activeExperiment,
  projectName = "Default Project",
  onStart,
  onStop,
  isActionLoading = false,
}: Partial<OptimizationLoopStatus>) {
  const { t } = useTranslation();
  const isRunning = status === "running" || status === "executing" || status === "designing" || status === "evaluating" || status === "analyzing" || status === "starting";
  const isPaused = status === "paused";
  const progressPercent = maxIterations > 0 ? (currentIteration / maxIterations) * 100 : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-lg ${
              isRunning ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-500"
            }`}
          >
            <RefreshCw className={`h-5 w-5 ${isRunning ? "animate-spin" : ""}`} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{t("dashboard.optimizationLoop")}</h3>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span className="flex items-center gap-1.5">
                <span
                  className={`h-2 w-2 rounded-full ${
                    isRunning ? "bg-blue-500" : isPaused ? "bg-orange-500" : status === "error" || status === "blocked" ? "bg-red-500" : "bg-slate-300"
                  }`}
                />
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </span>
              <span>·</span>
              <span>{projectName}</span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {isRunning ? (
            <button
              type="button"
              onClick={onStop}
              disabled={isActionLoading}
              className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />} {t("dashboard.stop")}
            </button>
          ) : (
            <button
              type="button"
              onClick={onStart}
              disabled={isActionLoading}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isActionLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} {t("dashboard.start")}
            </button>
          )}
          <Link
            to="/optimization"
            className="flex items-center justify-center rounded-lg border border-slate-200 p-1.5 text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition-colors"
          >
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 border-t border-slate-100 pt-4">
        <div>
          <div className="text-xs font-medium text-slate-500 mb-1">{t("dashboard.progress")}</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-slate-700">
              {currentIteration}/{maxIterations}
            </span>
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 mb-1">{t("dashboard.best_yield")}</div>
          <div className="text-sm font-semibold text-slate-700">
            {bestYield !== undefined ? `${bestYield.toFixed(2)}%` : "--"}
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-slate-500 mb-1">{t("dashboard.active_experiment")}</div>
          <div className="text-sm font-semibold text-slate-700 truncate">
            {activeExperiment || "--"}
          </div>
        </div>
      </div>
    </div>
  );
}
