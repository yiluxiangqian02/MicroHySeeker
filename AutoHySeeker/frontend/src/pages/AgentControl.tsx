import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Play, Square, RotateCw, Activity, Clock, CheckCircle, XCircle, Download } from "lucide-react";
import { AGENT_DEFINITIONS } from "@/stores/agentStore";

// Mock agent status data - replace with real API calls
interface AgentStatus {
  id: string;
  status: "running" | "idle" | "error" | "disabled";
  currentTask?: string;
  queuedTasks: number;
  metrics: {
    todayTokens: number;
    totalTokens: number;
    avgResponseTime: number;
    successRate: number;
    errorCount: number;
  };
  logs: Array<{
    timestamp: string;
    level: "INFO" | "WARNING" | "ERROR";
    message: string;
  }>;
}

const mockAgentStatuses: Record<string, AgentStatus> = {
  C1: {
    id: "C1",
    status: "running",
    currentTask: "Analyzing CV data for experiment #1234",
    queuedTasks: 2,
    metrics: {
      todayTokens: 15420,
      totalTokens: 234567,
      avgResponseTime: 2.3,
      successRate: 98.5,
      errorCount: 3
    },
    logs: [
      { timestamp: "2026-03-10T14:32:15", level: "INFO", message: "Started analysis task for experiment #1234" },
      { timestamp: "2026-03-10T14:30:42", level: "INFO", message: "Completed analysis for experiment #1233" },
      { timestamp: "2026-03-10T14:28:10", level: "WARNING", message: "High token usage detected" }
    ]
  },
  D2: {
    id: "D2",
    status: "idle",
    queuedTasks: 0,
    metrics: {
      todayTokens: 8920,
      totalTokens: 156789,
      avgResponseTime: 1.8,
      successRate: 96.2,
      errorCount: 8
    },
    logs: [
      { timestamp: "2026-03-10T14:15:30", level: "INFO", message: "Diagnostics check completed successfully" }
    ]
  },
  D3: {
    id: "D3",
    status: "running",
    currentTask: "Designing experiment parameters",
    queuedTasks: 1,
    metrics: {
      todayTokens: 12340,
      totalTokens: 198765,
      avgResponseTime: 3.1,
      successRate: 97.8,
      errorCount: 5
    },
    logs: [
      { timestamp: "2026-03-10T14:35:20", level: "INFO", message: "Generating experiment design" },
      { timestamp: "2026-03-10T14:33:45", level: "INFO", message: "Retrieved historical data" }
    ]
  },
  C2: {
    id: "C2",
    status: "error",
    queuedTasks: 0,
    metrics: {
      todayTokens: 5670,
      totalTokens: 123456,
      avgResponseTime: 2.0,
      successRate: 94.1,
      errorCount: 12
    },
    logs: [
      { timestamp: "2026-03-10T14:36:00", level: "ERROR", message: "Connection timeout to monitoring service" },
      { timestamp: "2026-03-10T14:30:15", level: "WARNING", message: "Slow response from API" }
    ]
  },
  C3: {
    id: "C3",
    status: "idle",
    queuedTasks: 0,
    metrics: {
      todayTokens: 3450,
      totalTokens: 87654,
      avgResponseTime: 1.5,
      successRate: 99.1,
      errorCount: 2
    },
    logs: [
      { timestamp: "2026-03-10T14:20:00", level: "INFO", message: "Knowledge base indexed successfully" }
    ]
  }
};

export function AgentControl() {
  const { t } = useTranslation();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [logFilter, setLogFilter] = useState<"ALL" | "INFO" | "WARNING" | "ERROR">("ALL");

  const handleStart = (agentId: string) => {
    console.log(`Starting agent ${agentId}`);
    // TODO: Call API to start agent
  };

  const handleStop = (agentId: string) => {
    console.log(`Stopping agent ${agentId}`);
    // TODO: Call API to stop agent
  };

  const handleRestart = (agentId: string) => {
    console.log(`Restarting agent ${agentId}`);
    // TODO: Call API to restart agent
  };

  const handleStartAll = () => {
    console.log("Starting all agents");
    // TODO: Call API to start all agents
  };

  const handleStopAll = () => {
    console.log("Stopping all agents");
    // TODO: Call API to stop all agents
  };

  const handleExportLogs = () => {
    if (!selectedAgent) return;
    const agent = mockAgentStatuses[selectedAgent];
    const logsText = agent.logs.map(log =>
      `[${log.timestamp}] ${log.level}: ${log.message}`
    ).join('\n');
    const blob = new Blob([logsText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agent-${selectedAgent}-logs-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running": return "bg-green-500";
      case "idle": return "bg-gray-400";
      case "error": return "bg-red-500";
      case "disabled": return "bg-slate-300";
      default: return "bg-gray-400";
    }
  };

  const selectedAgentData = selectedAgent ? mockAgentStatuses[selectedAgent] : null;
  const filteredLogs = selectedAgentData?.logs.filter(log =>
    logFilter === "ALL" || log.level === logFilter
  ) || [];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{t("agents.title")}</h2>
          <p className="mt-1 text-sm text-slate-500">{t("agents.subtitle")}</p>
          <p className="mt-3 max-w-3xl rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm leading-6 text-blue-900">
            这些不是给用户理解系统架构用的“内部 Agent 编号”，而是可以直接承担科研任务的 AI 角色：
            <strong>设计方案、监护运行、解读结果、排查故障、检索经验</strong>。
            如果后续保留这个页面，建议继续强化“什么时候找谁”，弱化 token 和控制台心智。
          </p>
        </div>

        {/* Bulk operations */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleStartAll}
            className="flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
          >
            <Play className="h-4 w-4" />
            {t("agents.startAll")}
          </button>
          <button
            onClick={handleStopAll}
            className="flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
          >
            <Square className="h-4 w-4" />
            {t("agents.stopAll")}
          </button>
        </div>
      </div>

      {/* Agent status cards grid */}
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {AGENT_DEFINITIONS.map((def) => {
          const status = mockAgentStatuses[def.id];
          return (
            <div
              key={def.id}
              className={`rounded-xl border ${
                selectedAgent === def.id ? "border-blue-500 ring-2 ring-blue-200" : "border-slate-200"
              } bg-white p-4 shadow-sm cursor-pointer transition-all hover:shadow-md`}
              onClick={() => setSelectedAgent(def.id)}
            >
              {/* Agent header */}
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`inline-block h-3 w-3 rounded-full ${getStatusColor(status.status)}`} />
                    <h3 className="font-semibold text-slate-900">{def.name}</h3>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{def.description}</p>
                </div>
              </div>

              {/* Current task */}
              {status.currentTask && (
                <div className="mt-3 rounded-md bg-blue-50 px-3 py-2">
                  <p className="text-xs font-medium text-blue-900">{t("agents.currentTask")}</p>
                  <p className="mt-0.5 text-xs text-blue-700">{status.currentTask}</p>
                </div>
              )}

              {/* Metrics */}
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <p className="text-slate-500">{t("agents.tokenUsage")}</p>
                  <p className="font-semibold text-slate-900">{status.metrics.todayTokens.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-slate-500">{t("agents.successRate")}</p>
                  <p className="font-semibold text-slate-900">{status.metrics.successRate}%</p>
                </div>
                <div>
                  <p className="text-slate-500">{t("agents.responseTime")}</p>
                  <p className="font-semibold text-slate-900">{status.metrics.avgResponseTime}s</p>
                </div>
                <div>
                  <p className="text-slate-500">{t("agents.taskQueue")}</p>
                  <p className="font-semibold text-slate-900">{status.queuedTasks} {t("agents.waitingTasks")}</p>
                </div>
              </div>

              {/* Control buttons */}
              <div className="mt-3 flex gap-2">
                <button
                  onClick={(e) => { e.stopPropagation(); handleStart(def.id); }}
                  disabled={status.status === "running"}
                  className="flex-1 flex items-center justify-center gap-1 rounded-md bg-green-600 px-2 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="h-3 w-3" />
                  {t("agents.startAgent")}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleStop(def.id); }}
                  disabled={status.status !== "running"}
                  className="flex-1 flex items-center justify-center gap-1 rounded-md bg-red-600 px-2 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Square className="h-3 w-3" />
                  {t("agents.stopAgent")}
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleRestart(def.id); }}
                  className="flex items-center justify-center rounded-md border border-slate-300 px-2 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  <RotateCw className="h-3 w-3" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Detailed view for selected agent */}
      {selectedAgentData && (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Performance metrics */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <Activity className="h-5 w-5 text-blue-600" />
              {t("agents.performance")}
            </h3>
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{t("agents.tokenUsage")} ({t("agents.todayTokens")})</span>
                <span className="font-semibold text-slate-900">{selectedAgentData.metrics.todayTokens.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{t("agents.tokenUsage")} ({t("agents.totalTokens")})</span>
                <span className="font-semibold text-slate-900">{selectedAgentData.metrics.totalTokens.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{t("agents.avgResponseTime")}</span>
                <span className="font-semibold text-slate-900">{selectedAgentData.metrics.avgResponseTime}s</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{t("agents.successRate")}</span>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="font-semibold text-slate-900">{selectedAgentData.metrics.successRate}%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">{t("agents.errorCount")}</span>
                <div className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="font-semibold text-slate-900">{selectedAgentData.metrics.errorCount}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Logs viewer */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Clock className="h-5 w-5 text-blue-600" />
                {t("agents.recentLogs")}
              </h3>
              <button
                onClick={handleExportLogs}
                className="flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Download className="h-3 w-3" />
                {t("agents.exportLogs")}
              </button>
            </div>

            {/* Log filter */}
            <div className="mt-3 flex gap-2">
              {(["ALL", "INFO", "WARNING", "ERROR"] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => setLogFilter(level)}
                  className={`rounded-md px-2 py-1 text-xs font-medium ${
                    logFilter === level
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  {level === "ALL" ? t("agents.allLevels") : t(`agents.${level.toLowerCase()}` as any)}
                </button>
              ))}
            </div>

            {/* Log entries */}
            <div className="mt-3 max-h-64 space-y-2 overflow-y-auto rounded-md bg-slate-900 p-3">
              {filteredLogs.length === 0 ? (
                <p className="text-xs text-slate-400">{t("agents.noLogs")}</p>
              ) : (
                filteredLogs.map((log, idx) => (
                  <div key={idx} className="text-xs font-mono">
                    <span className="text-slate-500">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{" "}
                    <span
                      className={
                        log.level === "ERROR"
                          ? "text-red-400"
                          : log.level === "WARNING"
                          ? "text-yellow-400"
                          : "text-green-400"
                      }
                    >
                      {log.level}
                    </span>
                    : <span className="text-slate-100">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
