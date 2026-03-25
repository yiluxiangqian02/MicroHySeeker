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

export interface AgentUsageStats {
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
}

export type AgentId =
  | "orchestrator"
  | "experiment_designer"
  | "experiment_executor"
  | "diagnostics_expert"
  | "chat"
  | "heartbeat_inspector";

export interface AgentModelConfig {
  enabled: boolean;
  primaryModel: string;
  fallbackModel: string;
  apiKey: string;
  baseUrl?: string;
  temperature?: number;
  maxTokens?: number | null;
  displayName?: string;
}

export interface AgentConfigSaveRequest {
  agentId: AgentId;
  config: AgentModelConfig;
}

export interface AgentConfigSaveResponse {
  ok: boolean;
  message?: string;
}

export interface AgentTestRequest {
  agentId: AgentId;
  task?: Record<string, unknown>;
}

export interface AgentTestResponse {
  ok: boolean;
  agentId?: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  durationMs?: number;
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

export interface AgentModelOption {
  value: string;
  label: string;
}

export interface AgentModelRecord {
  agent_name: AgentId;
  display_name: string;
  enabled: boolean;
  primary_model: string;
  fallback_model: string;
  api_key: string;
  temperature: number;
  max_tokens: number | null;
  base_url: string;
}

export interface AgentModelsResponse {
  ok: boolean;
  defaults: {
    model: string;
    fallback_model: string;
    base_url: string;
  };
  available_models: AgentModelOption[];
  agents: Partial<Record<AgentId, AgentModelRecord>>;
}

export interface AgentModelUpdateRequest {
  enabled?: boolean;
  primary_model?: string;
  fallback_model?: string;
  api_key?: string;
  temperature?: number;
  max_tokens?: number | null;
  base_url?: string;
}

export interface AgentModelUpdateResponse {
  ok: boolean;
  agent: AgentModelRecord;
}

// ── Dashboard / realtime monitoring types ─────────────────────────────────────
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

