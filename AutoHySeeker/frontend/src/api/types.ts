export interface HealthResponse {
  status: string;
  service: string;
}

export interface ExperimentListItem {
  run_dir: string;
  day: string;
  name: string;
  has_echem_dir: boolean;
  csv_count: number;
}

export interface ExperimentsResponse {
  count: number;
  items: ExperimentListItem[];
}

export interface LatestExperimentResponse {
  latest: ExperimentListItem;
  details: Record<string, unknown>;
}

export interface TaskCreateRequest {
  task_type?: string;
  payload?: Record<string, unknown>;
}

export interface TaskRecord {
  task_id: string;
  status: string;
  task_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export type DiagnosticsAction = "analyze_failure" | "check_health";

export interface DiagnosticsInvokeRequest {
  action: DiagnosticsAction;
  run_dir?: string;
  data_dir?: string;
  recent_n?: number;
  context?: Record<string, unknown>;
}

export interface DiagnosticsFinding {
  severity?: string;
  category?: string;
  component?: string;
  message?: string;
  evidence?: unknown;
  [key: string]: unknown;
}

export interface DiagnosticsReport {
  action: string;
  total_findings: number;
  severity_counts: Record<string, number>;
  findings: DiagnosticsFinding[];
  [key: string]: unknown;
}

export interface DiagnosticsResponse {
  ok: boolean;
  action: string;
  result: DiagnosticsReport | null;
  error?: string | null;
}

export type ContextAction = "contextualize" | "suggest";

export interface ContextInvokeRequest {
  action: ContextAction;
  run_dir?: string;
  history_dir?: string;
  previous_results?: Array<Record<string, unknown>>;
  metrics?: string[];
  threshold_sigma?: number;
  max_history?: number;
  context_data?: Record<string, unknown>;
  goal?: string;
  name?: string;
  description?: string;
  tags?: string[];
  extra_context?: Record<string, unknown>;
}

export interface ContextSkillResult<T = Record<string, unknown>> {
  success: boolean;
  data: T;
  message: string;
  artifacts?: unknown[];
}

export interface ContextResponse {
  ok: boolean;
  action: string;
  result: ContextSkillResult | Record<string, unknown> | null;
  error?: string | null;
}

export interface AgentInvokeRequest {
  task?: Record<string, unknown>;
  context?: Record<string, unknown>;
  messages?: Array<Record<string, unknown>>;
  current_agent?: string | null;
}

export interface AgentInvokeResponse {
  ok: boolean;
  result: Record<string, unknown> | null;
  state: Record<string, unknown>;
}

// ── Dashboard / realtime monitoring types ─────────────────────────────────────

export type AgentId = "C1" | "C2" | "D1" | "D2" | "D3";
export type AgentStatus = "idle" | "working" | "error";

export interface AgentState {
  id: AgentId;
  name: string;
  status: AgentStatus;
  lastActivity?: string;
  currentTask?: string;
}

export type ExperimentRunStatus = "idle" | "running" | "completed" | "failed";

export interface ExperimentProgressState {
  runId?: string;
  runName?: string;
  status: ExperimentRunStatus;
  progressPercent: number;
  currentStep?: string;
  elapsedSeconds?: number;
}

export interface EchemDataPoint {
  /** Relative seconds from dashboard open */
  t: number;
  voltage?: number;
  current?: number;
  power?: number;
}

export type LogLevel = "info" | "warning" | "error" | "debug";

export interface ExperimentLogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  agent?: string;
  message: string;
}

export interface DashboardSnapshot {
  experiment: ExperimentProgressState;
  agents: AgentState[];
  chartData: EchemDataPoint[];
  logs: ExperimentLogEntry[];
  lastUpdated: string;
}

export interface EmergencyStopResponse {
  ok: boolean;
  message: string;
}

