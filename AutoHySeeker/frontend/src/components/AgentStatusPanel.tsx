import type { AgentState, AgentStatus } from "@/api/types";

interface Props {
  agents: AgentState[];
}

const STATUS_STYLE: Record<AgentStatus, { dot: string; badge: string; label: string }> = {
  idle: {
    dot: "bg-slate-300",
    badge: "bg-slate-100 text-slate-500",
    label: "Idle",
  },
  working: {
    dot: "bg-amber-400 animate-pulse",
    badge: "bg-amber-50 text-amber-700",
    label: "Working",
  },
  error: {
    dot: "bg-red-500",
    badge: "bg-red-50 text-red-700",
    label: "Error",
  },
};

function AgentCard({ agent }: { agent: AgentState }) {
  const style = STATUS_STYLE[agent.status];
  return (
    <div className="flex items-start gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <span
        className={`mt-1.5 inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full ${style.dot}`}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-slate-800">{agent.id}</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>
            {style.label}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs text-slate-500">{agent.name}</p>
        {agent.currentTask && (
          <p className="mt-0.5 truncate text-xs text-amber-600">{agent.currentTask}</p>
        )}
      </div>
    </div>
  );
}

export function AgentStatusPanel({ agents }: Props) {
  const working = agents.filter((a) => a.status === "working").length;
  const errors = agents.filter((a) => a.status === "error").length;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Agent Status
        </h3>
        <div className="flex gap-2 text-xs">
          {working > 0 && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-700">
              {working} active
            </span>
          )}
          {errors > 0 && (
            <span className="rounded-full bg-red-100 px-2 py-0.5 font-medium text-red-700">
              {errors} error
            </span>
          )}
          {working === 0 && errors === 0 && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-500">
              all idle
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>
    </div>
  );
}
