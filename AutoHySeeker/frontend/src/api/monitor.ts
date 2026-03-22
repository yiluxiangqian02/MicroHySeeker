import { apiClient } from "./client";

export interface MonitorStatus {
  active_experiment_id: string | null;
  heartbeat_enabled: boolean;
  l1_status: string;
  l2_status: string;
  last_heartbeat: string | null;
  l1_alerts?: any[];
  l2_diagnostics?: string;
}

export interface MonitorConfig {
  heartbeat_enabled?: boolean;
  heartbeat_interval_s?: number;
  heartbeat_model?: string;
}

export const monitorApi = {
  getStatus: async () => {
    const res = await apiClient.get<MonitorStatus>("/api/monitor/status");
    return res.data;
  },
  toggleHeartbeat: async (enabled: boolean) => {
    const res = await apiClient.post("/api/monitor/toggle", { enabled });
    return res.data;
  },
  updateConfig: async (config: MonitorConfig) => {
    const res = await apiClient.put("/api/monitor/config", config);
    return res.data;
  }
};
