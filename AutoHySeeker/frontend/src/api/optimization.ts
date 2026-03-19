import { apiClient } from "./client";

export interface ParameterBoundary {
  min: number;
  max: number;
  type: "continuous" | "categorical" | "discrete";
  values?: (string | number)[];
}

export interface OptimizationConfig {
  targetFunction: "maximize_yield" | "minimize_cost" | "multi_objective";
  parameterSpace: Record<string, ParameterBoundary>;
  constraints: string[];
  maxIterations: number;
}

export interface OptimizationHistoryPoint {
  iteration: number;
  yield: number;
  objective_value?: number;
  params: Record<string, number | string>;
  experiment_id?: string;
}

export interface OptimizationState {
  status: "idle" | "running" | "paused" | "completed" | "error";
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
}

export const optimizationApi = {
  /** 获取当前项目或者全局的优化配置 */
  getConfig: async () => {
    const res = await apiClient.get<OptimizationConfig>("/api/optimization/config");
    return res.data;
  },

  /** 更新优化配置 */
  updateConfig: async (config: OptimizationConfig) => {
    const res = await apiClient.put<{ ok: boolean }>("/api/optimization/config", config);
    return res.data;
  },

  /** 获取当前的优化循环状态与历史 */
  getState: async () => {
    const res = await apiClient.get<OptimizationState>("/api/optimization/state");
    return res.data;
  },

  /** 启动新的优化循环 */
  start: async () => {
    const res = await apiClient.post<{ ok: boolean }>("/api/optimization/start");
    return res.data;
  },

  /** 停止或暂停当前的优化循环 */
  stop: async () => {
    const res = await apiClient.post<{ ok: boolean }>("/api/optimization/stop");
    return res.data;
  }
};
