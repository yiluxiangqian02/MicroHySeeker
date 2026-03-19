import { useMemo } from "react";
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

  // Mock data for new Dashboard components
  const mockOptimizationStatus = {
    status: "running" as const,
    currentIteration: 3,
    maxIterations: 10,
    bestYield: 85.4,
    activeExperiment: "Exp-003-HER-Opt",
    projectName: "Project Alpha"
  };

  const mockRecentExperiments = [
    { id: "exp_1", name: "Exp-003-HER-Opt", status: "running" as const, timeAgo: "10 mins ago" },
    { id: "exp_2", name: "Exp-002-Base", status: "completed" as const, timeAgo: "2 hours ago" },
    { id: "exp_3", name: "Exp-001-Test", status: "failed" as const, timeAgo: "1 day ago" },
  ];

  const mockNotifications = [
    { id: "no_1", type: "warning" as const, message: "Pump A pressure slightly above normal range.", timeAgo: "5 mins ago" },
    { id: "no_2", type: "info" as const, message: "Agent D3 started designing the next iteration.", timeAgo: "10 mins ago" },
    { id: "no_3", type: "error" as const, message: "Connection to potentiostat temporarily lost.", timeAgo: "1 hour ago" }
  ];

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
          <OptimizationStatusCard {...mockOptimizationStatus} />
        </div>
        <div className="lg:col-span-2">
          <RecentExperimentsCard experiments={mockRecentExperiments} />
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
          <SystemNotificationsCard notifications={mockNotifications} />
        </div>
      </motion.div>

      {/* ── Log panel ─────────────────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <ExperimentLog logs={snapshot.logs} />
      </motion.div>
    </motion.div>
  );
}
