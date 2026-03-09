import { useMemo } from "react";
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

  return (
    <div className="space-y-5">
      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
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
                  className="font-medium text-blue-600 hover:text-blue-700"
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
      </div>

      {/* ── Poll error banner ─────────────────────────────────────────────── */}
      {pollError && !isLoading && (
        <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-800">
            <span className="font-semibold">Connection error:</span> {pollError.message}
          </p>
          <button
            type="button"
            onClick={refresh}
            className="text-sm font-medium text-red-700 underline hover:text-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── Top row: Progress + Agents ────────────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ExperimentProgress experiment={snapshot.experiment} />
        </div>
        <div className="lg:col-span-2">
          <AgentStatusPanel agents={snapshot.agents} />
        </div>
      </div>

      {/* ── Realtime chart ────────────────────────────────────────────────── */}
      <RealtimeChart data={snapshot.chartData} />

      {/* ── Log panel ─────────────────────────────────────────────────────── */}
      <ExperimentLog logs={snapshot.logs} />
    </div>
  );
}
