import type { ExperimentProgressState } from "@/api/types";

interface Props {
  experiment: ExperimentProgressState;
}

const STATUS_CONFIG = {
  idle: {
    label: "Idle",
    barColor: "bg-slate-300",
    textColor: "text-slate-500",
    dotColor: "bg-slate-400",
    pulse: false,
  },
  running: {
    label: "Running",
    barColor: "bg-blue-500",
    textColor: "text-blue-700",
    dotColor: "bg-blue-500",
    pulse: true,
  },
  completed: {
    label: "Completed",
    barColor: "bg-green-500",
    textColor: "text-green-700",
    dotColor: "bg-green-500",
    pulse: false,
  },
  failed: {
    label: "Failed",
    barColor: "bg-red-500",
    textColor: "text-red-700",
    dotColor: "bg-red-500",
    pulse: false,
  },
} as const;

function formatElapsed(seconds?: number): string {
  if (seconds === undefined) return "--";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function ExperimentProgress({ experiment }: Props) {
  const cfg = STATUS_CONFIG[experiment.status];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Experiment Progress
        </h3>
        <span className={`flex items-center gap-1.5 text-xs font-semibold ${cfg.textColor}`}>
          <span
            className={`inline-block h-2 w-2 rounded-full ${cfg.dotColor}${cfg.pulse ? " animate-pulse" : ""}`}
            aria-hidden="true"
          />
          {cfg.label}
        </span>
      </div>

      <div className="mt-3 space-y-3">
        <div>
          <p className="truncate text-base font-semibold text-slate-900">
            {experiment.runName ?? "No active experiment"}
          </p>
          {experiment.runId && (
            <p className="truncate font-mono text-xs text-slate-400">{experiment.runId}</p>
          )}
        </div>

        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-500">
            <span>{experiment.currentStep ?? "Waiting"}</span>
            <span className="font-medium">{experiment.progressPercent}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all duration-500 ${cfg.barColor}`}
              style={{ width: `${experiment.progressPercent}%` }}
            />
          </div>
        </div>

        <p className="text-xs text-slate-500">
          Elapsed:{" "}
          <span className="font-medium text-slate-700">{formatElapsed(experiment.elapsedSeconds)}</span>
        </p>
      </div>
    </div>
  );
}
