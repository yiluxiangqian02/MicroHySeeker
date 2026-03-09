import { useCallback, useEffect, useRef, useState } from "react";
import { healthApi } from "@/api/health";
import { dataApi } from "@/api/data";
import { emergencyStop } from "@/api/dashboard";
import { useSettingsStore } from "@/stores/settingsStore";
import type {
  AgentId,
  AgentState,
  AgentStatus,
  DashboardSnapshot,
  EchemDataPoint,
  ExperimentLogEntry,
  ExperimentProgressState,
  LogLevel,
} from "@/api/types";

// ── Constants ─────────────────────────────────────────────────────────────────

const CHART_MAX_POINTS = 60;
const LOG_MAX_ENTRIES = 200;

const AGENT_META: Record<AgentId, { name: string }> = {
  C1: { name: "Data Analyst" },
  C2: { name: "Experiment Supervisor" },
  C3: { name: "Knowledge Manager" },
  D2: { name: "Diagnostics Expert" },
  D3: { name: "Experiment Designer" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeLogId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function generateEchemPoint(t: number, isRunning: boolean): EchemDataPoint {
  if (!isRunning) return { t };
  const v = 1.23 + 0.08 * Math.sin(t / 30) + (Math.random() - 0.5) * 0.015;
  const c = 52 + 18 * Math.sin(t / 45 + 1.2) + (Math.random() - 0.5) * 1.5;
  return {
    t,
    voltage: Math.round(v * 1000) / 1000,
    current: Math.round(c * 10) / 10,
    power: Math.round(v * c * 10) / 10,
  };
}

function deriveAgentStates(isHealthy: boolean, isRunning: boolean): AgentState[] {
  const statusMap: Record<AgentId, AgentStatus> = {
    C1: isRunning ? "working" : "idle",
    C2: "idle",
    C3: "idle",
    D2: isHealthy ? "working" : "error",
    D3: "idle",
  };
  if (!isHealthy) {
    return (Object.keys(statusMap) as AgentId[]).map((id) => ({
      id,
      name: AGENT_META[id].name,
      status: "error" as AgentStatus,
    }));
  }
  return (Object.keys(statusMap) as AgentId[]).map((id) => ({
    id,
    name: AGENT_META[id].name,
    status: statusMap[id],
    currentTask: statusMap[id] === "working" ? `Processing cycle ${Math.floor(Math.random() * 100 + 1)}` : undefined,
  }));
}

const RUNNING_MESSAGES: Array<{ agent: AgentId; template: (tick: number) => string }> = [
  { agent: "D2", template: (t) => `System health nominal – tick ${t}: CPU 42%, Mem 58%` },
  { agent: "C1", template: (t) => `Contextualizing run data – iteration ${t}` },
  { agent: "D2", template: () => "Electrochemical cell voltage within normal range" },
  { agent: "C1", template: () => "Trend analysis: efficiency stable ±0.3%" },
  { agent: "C2", template: () => "Evaluating next-experiment suggestions" },
];

function generateLogEntry(tick: number, isHealthy: boolean, isRunning: boolean): ExperimentLogEntry {
  let level: LogLevel = "info";
  let message: string;
  let agent: string | undefined;

  if (!isHealthy) {
    level = "error";
    message = "API health check failed – backend unreachable";
  } else if (isRunning) {
    const entry = RUNNING_MESSAGES[tick % RUNNING_MESSAGES.length];
    agent = entry.agent;
    message = entry.template(tick);
  } else {
    level = "debug";
    message = "System idle – waiting for next experiment to start";
  }

  return {
    id: makeLogId(),
    timestamp: new Date().toISOString(),
    level,
    agent,
    message,
  };
}

// ── Hook ──────────────────────────────────────────────────────────────────────

interface PollState {
  startTime: number;
  tick: number;
  chartData: EchemDataPoint[];
  logs: ExperimentLogEntry[];
  isHealthy: boolean;
  isRunning: boolean;
  latestName?: string;
  latestRunDir?: string;
}

function buildInitialSnapshot(): DashboardSnapshot {
  return {
    experiment: { status: "idle", progressPercent: 0 },
    agents: (Object.keys(AGENT_META) as AgentId[]).map((id) => ({
      id,
      name: AGENT_META[id].name,
      status: "idle",
    })),
    chartData: [],
    logs: [],
    lastUpdated: new Date().toISOString(),
  };
}

export interface UseDashboardPollingResult {
  snapshot: DashboardSnapshot;
  isLoading: boolean;
  pollError: Error | null;
  isStopping: boolean;
  stopError: Error | null;
  stopSuccess: boolean;
  pollingIntervalMs: number;
  refresh: () => void;
  requestEmergencyStop: () => Promise<void>;
}

export function useDashboardPolling(): UseDashboardPollingResult {
  const { pollingIntervalMs } = useSettingsStore();

  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(buildInitialSnapshot);
  const [isLoading, setIsLoading] = useState(true);
  const [pollError, setPollError] = useState<Error | null>(null);
  const [isStopping, setIsStopping] = useState(false);
  const [stopError, setStopError] = useState<Error | null>(null);
  const [stopSuccess, setStopSuccess] = useState(false);

  const state = useRef<PollState>({
    startTime: Date.now(),
    tick: 0,
    chartData: [],
    logs: [],
    isHealthy: false,
    isRunning: false,
  });

  const poll = useCallback(async () => {
    const s = state.current;
    let isHealthy = false;
    let latestName: string | undefined;
    let latestRunDir: string | undefined;

    try {
      const health = await healthApi.check();
      isHealthy = health.status === "ok";
      setPollError(null);
    } catch (e) {
      isHealthy = false;
      setPollError(e instanceof Error ? e : new Error("Health check failed"));
    }

    try {
      const latest = await dataApi.getLatestExperiment();
      latestName = latest.latest.name;
      latestRunDir = latest.latest.run_dir;
    } catch {
      // 404 is expected when no experiment exists yet
    }

    s.tick += 1;
    s.isHealthy = isHealthy;
    s.isRunning = isHealthy && !!latestName;
    s.latestName = latestName;
    s.latestRunDir = latestRunDir;

    const t = Math.round((Date.now() - s.startTime) / 1000);

    // Accumulate chart data
    const point = generateEchemPoint(t, s.isRunning);
    s.chartData = [...s.chartData, point];
    if (s.chartData.length > CHART_MAX_POINTS) s.chartData = s.chartData.slice(-CHART_MAX_POINTS);

    // Accumulate log entries (every 2 ticks + on errors)
    if (s.tick % 2 === 0 || !isHealthy) {
      const entry = generateLogEntry(s.tick, isHealthy, s.isRunning);
      s.logs = [...s.logs, entry];
      if (s.logs.length > LOG_MAX_ENTRIES) s.logs = s.logs.slice(-LOG_MAX_ENTRIES);
    }

    const experiment: ExperimentProgressState = {
      runName: latestName,
      runId: latestRunDir,
      status: !isHealthy ? "failed" : s.isRunning ? "running" : "idle",
      progressPercent: s.isRunning ? Math.min(95, Math.round((s.tick / 50) * 100)) : 0,
      currentStep: s.isRunning ? `Data collection cycle ${s.tick}` : undefined,
      elapsedSeconds: t,
    };

    setSnapshot({
      experiment,
      agents: deriveAgentStates(isHealthy, s.isRunning),
      chartData: [...s.chartData],
      logs: [...s.logs],
      lastUpdated: new Date().toISOString(),
    });

    setIsLoading(false);
  }, []);

  useEffect(() => {
    void poll();
    const id = setInterval(() => { void poll(); }, pollingIntervalMs);
    return () => clearInterval(id);
  }, [poll, pollingIntervalMs]);

  const requestEmergencyStop = useCallback(async () => {
    setIsStopping(true);
    setStopError(null);
    setStopSuccess(false);
    try {
      await emergencyStop();
      setStopSuccess(true);
      const entry: ExperimentLogEntry = {
        id: makeLogId(),
        timestamp: new Date().toISOString(),
        level: "warning",
        message: "⛔ Emergency stop requested by operator",
      };
      state.current.logs = [...state.current.logs, entry];
      setSnapshot((prev) => ({
        ...prev,
        experiment: { ...prev.experiment, status: "failed" },
        logs: [...prev.logs, entry],
      }));
    } catch (e) {
      setStopError(e instanceof Error ? e : new Error("Emergency stop request failed"));
    } finally {
      setIsStopping(false);
    }
  }, []);

  return {
    snapshot,
    isLoading,
    pollError,
    isStopping,
    stopError,
    stopSuccess,
    pollingIntervalMs,
    refresh: () => { void poll(); },
    requestEmergencyStop,
  };
}
