import { useMemo } from "react";
import { motion } from "framer-motion";
import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { EmergencyStop } from "@/components/EmergencyStop";
import { ExperimentLog } from "@/components/ExperimentLog";
import { ExperimentProgress } from "@/components/ExperimentProgress";
import { RealtimeChart } from "@/components/RealtimeChart";
import { useDashboardPolling } from "@/hooks/useDashboardPolling";

function LastUpdatedBadge({ iso }: { iso: string }) {
  const formatted = useMemo(() => {
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
  }, [iso]);
  return <span className="text-xs text-slate-400">Updated {formatted}</span>;
}

export function Dashboard() {
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
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

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
          <h2 className="text-xl font-bold text-slate-900">Live Dashboard</h2>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            {isLoading ? (
              <span>Initializing…</span>
            ) : (
              <>
                <LastUpdatedBadge iso={snapshot.lastUpdated} />
                <span>·</span>
                <span>Polling every {pollingIntervalMs / 1000}s</span>
                <button
                  type="button"
                  onClick={refresh}
                  className="font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  Refresh now
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
              <span className="font-semibold">Connection error:</span> {pollError.message}
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
            Retry
          </button>
        </motion.div>
      )}

      {/* ── Top row: Progress + Agents ────────────────────────────────────── */}
      <motion.div variants={itemVariants} className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ExperimentProgress experiment={snapshot.experiment} />
        </div>
        <div className="lg:col-span-2">
          <AgentStatusPanel agents={snapshot.agents} />
        </div>
      </motion.div>

      {/* ── Realtime chart ────────────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <RealtimeChart data={snapshot.chartData} />
      </motion.div>

      {/* ── Log panel ─────────────────────────────────────────────────────── */}
      <motion.div variants={itemVariants}>
        <ExperimentLog logs={snapshot.logs} />
      </motion.div>
    </motion.div>
  );
}
