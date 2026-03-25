import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { EmergencyStop } from "@/components/EmergencyStop";
import { ExperimentLog } from "@/components/ExperimentLog";
import { ExperimentProgress } from "@/components/ExperimentProgress";
import { RealtimeChart } from "@/components/RealtimeChart";
import { OptimizationStatusCard } from "@/components/dashboard/OptimizationStatusCard";
import { RecentExperimentsCard } from "@/components/dashboard/RecentExperimentsCard";
import { SystemNotificationsCard } from "@/components/dashboard/SystemNotificationsCard";
import { useDashboardPolling } from "@/hooks/useDashboardPolling";
import { useOptimizationStore } from "@/stores/optimizationStore";

function LastUpdatedBadge({ iso }: { iso: string }) {
  const { t } = useTranslation();
  const formatted = useMemo(() => {
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
  }, [iso]);
  return <span className="text-xs text-slate-400">{t("dashboard.updated")} {formatted}</span>;
}

export function Dashboard() {
  const { t } = useTranslation();
  const {
    config: optimizationConfig,
    state: optimizationState,
    fetchConfigAndState: fetchOptimizationState,
  } = useOptimizationStore();
  const {
    snapshot,
    isLoading,
    pollError,
    isStopping,
    stopError,
    stopSuccess,
    pollingIntervalMs,
    refresh,
    requestEmergencyStop,
  } = useDashboardPolling();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.05, duration: 0.3 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  };

  useEffect(() => {
    const refreshOptimization = () => {
      fetchOptimizationState().catch(() => undefined);
    };

    refreshOptimization();
    const timer = window.setInterval(refreshOptimization, 5000);
    return () => window.clearInterval(timer);
  }, [fetchOptimizationState]);

  const optimizationStatus = useMemo(() => {
    const latestHistoryItem = optimizationState?.history[optimizationState.history.length - 1];
    return {
      status: optimizationState?.status ?? "idle",
      currentIteration: optimizationState?.currentIteration ?? 0,
      maxIterations: optimizationState?.maxIterations ?? 0,
      bestYield: optimizationState?.bestYield,
      activeExperiment: latestHistoryItem?.experiment_id ?? snapshot.experiment.runName,
      projectName: optimizationConfig?.goal ?? "Optimization Loop",
    };
  }, [optimizationConfig?.goal, optimizationState, snapshot.experiment.runName]);

  const recentExperiments = useMemo(() => (
    optimizationState?.history
      .slice(-3)
      .reverse()
      .map((item, index) => ({
        id: item.experiment_id || `optimization-${item.iteration}-${index}`,
        name: item.experiment_id || `Round ${item.iteration}`,
        status: item.status === "failed" ? "failed" as const : item.status === "completed" ? "completed" as const : "running" as const,
        timeAgo: `Round ${item.iteration}`,
      })) ?? []
  ), [optimizationState?.history]);

  const systemNotifications = useMemo(() => {
    const items = [];

    if (optimizationState?.pendingApproval) {
      items.push({
        id: "approval-pending",
        type: "warning" as const,
        message: `Optimization paused: ${optimizationState.pauseReason || "waiting for human approval"}`,
        timeAgo: "now",
      });
    }

    for (const [index, error] of (optimizationState?.errors ?? []).slice(-3).entries()) {
      items.push({
        id: `optimization-error-${index}`,
        type: "error" as const,
        message: error,
        timeAgo: "recent",
      });
    }

    if (items.length === 0 && optimizationState) {
      items.push({
        id: "optimization-status",
        type: "info" as const,
        message: `Optimization status: ${optimizationState.status}`,
        timeAgo: "live",
      });
    }

    return items;
  }, [optimizationState]);

  return (
    <motion.div
      className="space-y-5"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">{t("dashboard.live_dashboard")}</h2>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            {isLoading ? (
              <span>{t("dashboard.initializing")}</span>
            ) : (
              <>
                <LastUpdatedBadge iso={snapshot.lastUpdated} />
                <span>·</span>
                <span>{t("dashboard.polling_every")} {pollingIntervalMs / 1000}s</span>
                <button
                  type="button"
                  onClick={refresh}
                  className="font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  {t("dashboard.refresh_now")}
                </button>
              </>
            )}
          </div>
        </div>

        <EmergencyStop
          onStop={requestEmergencyStop}
          isStopping={isStopping}
          stopSuccess={stopSuccess}
          stopError={stopError}
        />
      </motion.div>

      {/* ── Poll error banner ─────────────────────────────────────────────── */}
      {pollError && !isLoading && (
        <motion.div
          variants={itemVariants}
          className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 shadow-sm"
        >
          <div className="text-sm text-red-800">
            <p>
              <span className="font-semibold">{t("dashboard.connection_error")}:</span> {pollError.message}
            </p>
            <p className="mt-0.5 text-xs text-red-600">
              Make sure the AutoHySeeker API server is running at{" "}
              <code className="font-mono">{import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8100"}</code>.
              Check <code className="font-mono">/health</code> and{" "}
              <code className="font-mono">/api/experiments/status</code> endpoints.
            </p>
          </div>
          <button
            type="button"
            onClick={refresh}
            className="ml-4 shrink-0 text-sm font-medium text-red-700 underline hover:text-red-900 transition-colors"
          >
            {t("common.retry") || "Retry"}
          </button>
        </motion.div>
      )}

      {/* ── Top row 1: Optimization Status + Recent Experiments ───────────── */}
      <motion.div variants={itemVariants} className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <OptimizationStatusCard {...optimizationStatus} />
        </div>
        <div className="lg:col-span-2">
          <RecentExperimentsCard experiments={recentExperiments} />
        </div>
      </motion.div>

      {/* ── Top row 2: Progress + Agents ──────────────────────────────────── */}
      <motion.div variants={itemVariants} className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ExperimentProgress experiment={snapshot.experiment} />
        </div>
        <div className="lg:col-span-2">
          <AgentStatusPanel agents={snapshot.agents} />
        </div>
      </motion.div>

      {/* ── Realtime chart + Notifications ────────────────────────────────── */}
      <motion.div variants={itemVariants} className="grid gap-4 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <RealtimeChart data={snapshot.chartData} />
        </div>
        <div className="lg:col-span-1">
          <SystemNotificationsCard notifications={systemNotifications} />
        </div>
      </motion.div>

      {/* ── Log panel ─────────────────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <ExperimentLog logs={snapshot.logs} />
      </motion.div>
    </motion.div>
  );
}
