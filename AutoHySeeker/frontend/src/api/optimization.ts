import { apiClient } from "./client";

export interface ParameterBoundary {
  min: number;
  max: number;
  type: "continuous" | "categorical" | "discrete";
  values?: Array<string | number>;
}

export interface OptimizationConfig {
  goal: string;
  targetMetric: string;
  direction: string;
  targetFunction: string;
  parameterSpace: Record<string, ParameterBoundary>;
  constraints: string[];
  maxIterations: number;
  templateId?: string;
  elements: string[];
}

export interface OptimizationHistoryPoint {
  iteration: number;
  yield: number;
  objective_value?: number;
  params: Record<string, number | string>;
  experiment_id?: string;
  status?: string;
}

export interface OptimizationState {
  status: "idle" | "running" | "paused" | "completed" | "error" | "stopped" | "blocked" | "starting" | "stopping" | "executing" | "designing" | "evaluating" | "analyzing";
  currentIteration: number;
  maxIterations: number;
  bestYield: number;
  bestParams: Record<string, number | string>;
  history: OptimizationHistoryPoint[];
  nextSuggestion?: {
    reason: string;
    suggestedParams: Record<string, number | string>;
    predictedYield: number;
  };
  pendingApproval?: Record<string, unknown> | null;
  pauseReason?: string | null;
  latestDecision?: Record<string, unknown> | null;
  lastApproval?: Record<string, unknown> | null;
  errors: string[];
  hardwareAvailable: boolean;
}

export interface OptimizationStatusResponse {
  running: boolean;
  status: string;
  current_round: number;
  max_rounds: number;
  best_result: {
    params?: Record<string, number | string>;
    metrics?: Record<string, number>;
  } | null;
  goal: string;
  target_metric: string;
  errors: string[];
  pending_approval?: Record<string, unknown> | null;
  pause_reason?: string | null;
  latest_decision?: Record<string, unknown> | null;
  last_approval?: Record<string, unknown> | null;
  hardware_available?: boolean;
}

export interface OptimizationHistoryResponse {
  history: Array<{
    round?: number;
    params?: Record<string, number | string>;
    metrics?: Record<string, number>;
    run_id?: string;
    status?: string;
  }>;
  best_result: {
    params?: Record<string, number | string>;
    metrics?: Record<string, number>;
  } | null;
  total_rounds: number;
}

export interface OptimizationStartRequest {
  goal: string;
  max_rounds: number;
  target_metric: string;
  direction: string;
  template_id?: string;
  elements?: string[];
  dry_run?: boolean;
}

const DEFAULT_ELEMENTS = ["Fe", "Co", "Ni"];

const buildParameterSpace = (elements: string[]): Record<string, ParameterBoundary> =>
  elements.reduce<Record<string, ParameterBoundary>>((acc, element) => {
    acc[element] = { type: "continuous", min: 0.05, max: 0.9 };
    return acc;
  }, {});

const pickPrimaryMetric = (
  metrics: Record<string, number> | undefined,
  targetMetric: string,
): number => {
  if (!metrics) {
    return 0;
  }
  if (typeof metrics[targetMetric] === "number") {
    return metrics[targetMetric];
  }
  const fallback = Object.values(metrics).find((value) => typeof value === "number");
  return typeof fallback === "number" ? fallback : 0;
};

export const mapOptimizationConfig = (status: OptimizationStatusResponse): OptimizationConfig => {
  const elements = Object.keys(status.best_result?.params ?? {});
  const normalizedElements = elements.length > 0 ? elements : DEFAULT_ELEMENTS;
  return {
    goal: status.goal || "Optimize experiment loop",
    targetMetric: status.target_metric || "overpotential_mV",
    direction: "minimize",
    targetFunction: status.target_metric || "optimization",
    parameterSpace: buildParameterSpace(normalizedElements),
    constraints: [],
    maxIterations: status.max_rounds || 0,
    templateId: "tpl_her_standard",
    elements: normalizedElements,
  };
};

export const mapOptimizationState = (
  status: OptimizationStatusResponse,
  history: OptimizationHistoryResponse,
): OptimizationState => {
  const targetMetric = status.target_metric || "overpotential_mV";
  const mappedHistory = history.history.map((item) => ({
    iteration: item.round || 0,
    yield: pickPrimaryMetric(item.metrics, targetMetric),
    objective_value: pickPrimaryMetric(item.metrics, targetMetric),
    params: item.params || {},
    experiment_id: item.run_id,
    status: item.status,
  }));

  const bestMetric = pickPrimaryMetric(status.best_result?.metrics, targetMetric);

  return {
    status: (status.status as OptimizationState["status"]) || "idle",
    currentIteration: status.current_round || 0,
    maxIterations: status.max_rounds || 0,
    bestYield: bestMetric,
    bestParams: status.best_result?.params || {},
    history: mappedHistory,
    pendingApproval: status.pending_approval ?? null,
    pauseReason: status.pause_reason ?? null,
    latestDecision: status.latest_decision ?? null,
    lastApproval: status.last_approval ?? null,
    errors: status.errors || [],
    hardwareAvailable: status.hardware_available ?? false,
  };
};

export const optimizationApi = {
  getStatus: async () => {
    const res = await apiClient.get<OptimizationStatusResponse>("/api/optimization/status");
    return res.data;
  },

  getHistory: async () => {
    const res = await apiClient.get<OptimizationHistoryResponse>("/api/optimization/history");
    return res.data;
  },

  start: async (payload: OptimizationStartRequest) => {
    const res = await apiClient.post("/api/optimization/start", payload);
    return res.data;
  },

  stop: async () => {
    const res = await apiClient.post("/api/optimization/stop");
    return res.data;
  },

  reset: async () => {
    const res = await apiClient.delete("/api/optimization/reset");
    return res.data;
  },
};
