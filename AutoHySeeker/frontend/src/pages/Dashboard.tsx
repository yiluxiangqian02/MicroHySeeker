import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { AgentStatusPanel } from "@/components/AgentStatusPanel";
import { EmergencyStop } from "@/components/EmergencyStop";
import { ExperimentLog } from "@/components/ExperimentLog";
import { ExperimentProgress } from "@/components/ExperimentProgress";
import { RealtimeChart } from "@/components/RealtimeChart";
import { OptimizationStatusCard } from "@/components/dashboard/OptimizationStatusCard";
import { RecentExperimentsCard } from "@/components/dashboard/RecentExperimentsCard";
import { SystemNotificationsCard } from "@/components/dashboard/SystemNotificationsCard";
import { HardwareStatusBadge } from "@/components/dashboard/HardwareStatusBadge";
import { useDashboardPolling } from "@/hooks/useDashboardPolling";
import { useOptimizationStore } from "@/stores/optimizationStore";
import { useSystemConfigStore } from "@/stores/systemConfigStore";
import type { AgentId, AgentState, AgentStatus, ExperimentProgressState, ExperimentLogEntry } from "@/api/types";

// ── Agent metadata ────────────────────────────────────────────────────────────

const AGENT_META: Record<AgentId, { name: string }> = {
  orchestrator: { name: "Orchestrator" },
  experiment_designer: { name: "Experiment Designer" },
  experiment_executor: { name: "Experiment Executor" },
  diagnostics_expert: { name: "Diagnostics Expert" },
  chat: { name: "Chat Agent" },
  heartbeat_inspector: { name: "Heartbeat Inspector" },
};

const ALL_AGENT_IDS = Object.keys(AGENT_META) as AgentId[];

// ── Derive agent states from real optimization status ─────────────────────────

function deriveAgentStatesFromOptimization(
  optimizationStatus: string | undefined,
  isHealthy: boolean,
): AgentState[] {
  if (!isHealthy) {
    return ALL_AGENT_IDS.map((id) => ({
      id,
      name: AGENT_META[id].name,
      status: "error" as AgentStatus,
    }));
  }

  const status = optimizationStatus ?? "idle";

  const agentActivity: Record<AgentId, { status: AgentStatus; task?: string }> = {
    orchestrator: { status: "idle" },
    experiment_designer: { status: "idle" },
    experiment_executor: { status: "idle" },
    diagnostics_expert: { status: "idle" },
    chat: { status: "idle" },
    heartbeat_inspector: { status: "idle" },
  };

  // Map optimization phase to active agent
  if (status === "running" || status === "evaluating") {
    agentActivity.orchestrator = { status: "working", task: `Optimization ${status}` };
  }
  if (status === "designing") {
    agentActivity.experiment_designer = { status: "working", task: "Designing next experiment" };
    agentActivity.orchestrator = { status: "working", task: "Coordinating design phase" };
  }
  if (status === "executing") {
    agentActivity.experiment_executor = { status: "working", task: "Executing experiment" };
    agentActivity.orchestrator = { status: "working", task: "Coordinating execution" };
  }
  if (status === "analyzing") {
    agentActivity.diagnostics_expert = { status: "working", task: "Analyzing results" };
    agentActivity.orchestrator = { status: "working", task: "Coordinating analysis" };
  }
  if (status === "starting") {
    agentActivity.orchestrator = { status: "working", task: "Initializing optimization loop" };
  }

  return ALL_AGENT_IDS.map((id) => ({
    id,
    name: AGENT_META[id].name,
    status: agentActivity[id].status,
    currentTask: agentActivity[id].task,
  }));
}

// ── Derive logs from optimization state ───────────────────────────────────────

function deriveLogsFromOptimization(
  optimizationStatus: string | undefined,
  errors: string[],
  currentIteration: number,
  pendingApproval: boolean,
): ExperimentLogEntry[] {
  const logs: ExperimentLogEntry[] = [];
  const now = new Date().toISOString();

  // Status log
  if (optimizationStatus && optimizationStatus !== "idle") {
    logs.push({
      id: `status-${optimizationStatus}`,
      timestamp: now,
      level: "info",
      agent: "orchestrator",
      message: `Optimization loop status: ${optimizationStatus}`,
    });
  }

  // Iteration info
  if (currentIteration > 0) {
    logs.push({
      id: `iteration-${currentIteration}`,
      timestamp: now,
      level: "info",
      agent: "orchestrator",
      message: `Current round: ${currentIteration}`,
    });
  }

  // Approval pending
  if (pendingApproval) {
    logs.push({
      id: "approval-pending",
      timestamp: now,
      level: "warning",
      agent: "orchestrator",
      message: "Human approval required — optimization paused",
    });
  }

  // Errors
  for (const [index, error] of errors.entries()) {
    logs.push({
      id: `error-${index}`,
      timestamp: now,
      level: "error",
      message: error,
    });
  }

  // If nothing at all, show idle
  if (logs.length === 0) {
    logs.push({
      id: "idle",
      timestamp: now,
      level: "debug",
      message: "System idle — no optimization running",
    });
  }

  return logs;
}

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
    isLoading: optimizationLoading,
    fetchConfigAndState: fetchOptimizationState,
    startLoop,
    stopLoop,
  } = useOptimizationStore();
  const {
    isHealthy,
    isLoading,
    pollError,
    isStopping,
    stopError,
    stopSuccess,
    pollingIntervalMs,
    lastUpdated,
    refresh,
    requestEmergencyStop,
  } = useDashboardPolling();
  const mhsStatus = useSystemConfigStore((s) => s.mhsStatus);


  useEffect(() => {
    const refreshOptimization = () => {
      fetchOptimizationState().catch(() => undefined);
    };

    refreshOptimization();
    const timer = window.setInterval(refreshOptimization, 5000);
    return () => window.clearInterval(timer);
  }, [fetchOptimizationState]);

  // ── All derived data from optimizationStore (real API) ──────────────────

  const optimizationStatus = useMemo(() => {
    const latestHistoryItem = optimizationState?.history[optimizationState.history.length - 1];
    return {
      status: optimizationState?.status ?? "idle",
      currentIteration: optimizationState?.currentIteration ?? 0,
      maxIterations: optimizationState?.maxIterations ?? 0,
      bestYield: optimizationState?.bestYield,
      activeExperiment: latestHistoryItem?.experiment_id,
      projectName: optimizationConfig?.goal ?? "Optimization Loop",
    };
  }, [optimizationConfig?.goal, optimizationState]);

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

    if (!isHealthy && !isLoading) {
      items.push({
        id: "backend-offline",
        type: "error" as const,
        message: "Backend API unreachable",
        timeAgo: "now",
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
  }, [optimizationState, isHealthy, isLoading]);

  // Derive experiment progress from real optimization state
  const experimentProgress: ExperimentProgressState = useMemo(() => {
    const status = optimizationState?.status;
    const isRunning = status === "running" || status === "designing" || status === "executing" || status === "analyzing" || status === "evaluating" || status === "starting";

    return {
      status: !isHealthy && !isLoading ? "failed" : isRunning ? "running" : status === "error" ? "failed" : status === "completed" ? "completed" : "idle",
      progressPercent: optimizationState?.maxIterations
        ? Math.round((optimizationState.currentIteration / optimizationState.maxIterations) * 100)
        : 0,
      currentStep: status && status !== "idle" ? `Phase: ${status}` : undefined,
      runName: optimizationConfig?.goal,
      elapsedSeconds: undefined,
    };
  }, [optimizationState, optimizationConfig, isHealthy, isLoading]);

  // Derive agent states from real optimization status
  const agentStates = useMemo(() =>
    deriveAgentStatesFromOptimization(optimizationState?.status, isHealthy),
    [optimizationState?.status, isHealthy],
  );

  // Derive logs from real optimization state
  const logs = useMemo(() =>
    deriveLogsFromOptimization(
      optimizationState?.status,
      optimizationState?.errors ?? [],
      optimizationState?.currentIteration ?? 0,
      !!optimizationState?.pendingApproval,
    ),
    [optimizationState],
  );

  // Empty chart data — no fake echem data; real data requires MicroHySeeker
  const chartData = useMemo(() => {
    // Build chart from optimization history metrics if available
    return (optimizationState?.history ?? []).map((item) => ({
      t: item.iteration,
      voltage: item.yield || undefined,
    }));
  }, [optimizationState?.history]);

  return (
    <div className="space-y-5">
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">{t("dashboard.live_dashboard")}</h2>
          <div className="flex items-center gap-3 text-xs text-slate-500">
            {isLoading ? (
              <span>{t("dashboard.initializing")}</span>
            ) : (
              <span>
                <LastUpdatedBadge iso={lastUpdated} />
                <span className="mx-1">·</span>
                {t("dashboard.polling_every")} {pollingIntervalMs / 1000}s
                <button
                  type="button"
                  onClick={refresh}
                  className="ml-2 font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  {t("dashboard.refresh_now")}
                </button>
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <HardwareStatusBadge
            isHealthy={isHealthy}
            isLoading={isLoading}
            hardwareAvailable={mhsStatus.online && mhsStatus.connected}
          />
          <EmergencyStop
            onStop={requestEmergencyStop}
            isStopping={isStopping}
            stopSuccess={stopSuccess}
            stopError={stopError}
          />
        </div>
      </div>

      {/* ── Poll error banner ─────────────────────────────────────────────── */}
      <div
        className="overflow-hidden transition-all duration-300"
        style={{ maxHeight: pollError && !isLoading ? 200 : 0, opacity: pollError && !isLoading ? 1 : 0 }}
      >
        <div className="flex items-center justify-between rounded-xl border border-red-200 bg-red-50 px-4 py-3 shadow-sm">
          <div className="text-sm text-red-800">
            <p>
              <span className="font-semibold">{t("dashboard.connection_error")}:</span> {pollError?.message}
            </p>
            <p className="mt-0.5 text-xs text-red-600">
              Make sure the AutoHySeeker API server is running at{" "}
              <code className="font-mono">{import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8200"}</code>.
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
        </div>
      </div>

      {/* ── Top row 1: Optimization Status + Recent Experiments ───────────── */}
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <OptimizationStatusCard
            {...optimizationStatus}
            onStart={startLoop}
            onStop={stopLoop}
            isActionLoading={optimizationLoading}
          />
        </div>
        <div className="lg:col-span-2">
          <RecentExperimentsCard experiments={recentExperiments} />
        </div>
      </div>

      {/* ── Top row 2: Progress + Agents ──────────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ExperimentProgress experiment={experimentProgress} />
        </div>
        <div className="lg:col-span-2">
          <AgentStatusPanel agents={agentStates} />
        </div>
      </div>

      {/* ── Realtime chart + Notifications ────────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <RealtimeChart data={chartData} />
        </div>
        <div className="lg:col-span-1">
          <SystemNotificationsCard notifications={systemNotifications} />
        </div>
      </div>

      {/* ── Log panel ─────────────────────────────────────────────────────── */}
      <div>
        <ExperimentLog logs={logs} />
      </div>
    </div>
  );
}
