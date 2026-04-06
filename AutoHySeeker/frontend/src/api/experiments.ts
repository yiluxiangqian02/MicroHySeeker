import { apiClient } from "./client";

export interface Experiment {
  exp_id: string;
  name: string;
  description: string;
  status: 'created' | 'running' | 'completed' | 'failed' | 'stopped';
  tags: string[];
  category?: string;
  execution_mode?: 'hardware' | 'simulated';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  steps?: Array<{
    step_type: string;
    description: string;
    params: Record<string, any>;
  }>;
  data: Array<{ x: number; y: number }>;
}

export const experimentsApi = {
  async list(): Promise<Experiment[]> {
    const response = await apiClient.get<Experiment[]>("/api/experiments");
    return response.data;
  },
  
  async get(id: string): Promise<Experiment> {
    const response = await apiClient.get<Experiment>(`/api/experiments/detail/${id}`);
    return response.data;
  },

  async execute(id: string): Promise<any> {
    const response = await apiClient.post(`/api/experiments/detail/${id}/execute`);
    return response.data;
  }
};