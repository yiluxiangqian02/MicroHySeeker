import { apiClient } from "@/api/client";
import type {
  AgentInvokeRequest,
  AgentInvokeResponse,
  AgentConfigSaveRequest,
  AgentConfigSaveResponse,
  AgentTestRequest,
  AgentTestResponse
} from "@/api/types";

export const agentsApi = {
  async invoke(payload: AgentInvokeRequest): Promise<AgentInvokeResponse> {
    const response = await apiClient.post<AgentInvokeResponse>("/agents/invoke", payload);
    return response.data;
  },

  async saveConfig(payload: AgentConfigSaveRequest): Promise<AgentConfigSaveResponse> {
    const response = await apiClient.post<AgentConfigSaveResponse>("/agents/config", payload);
    return response.data;
  },

  async test(payload: AgentTestRequest): Promise<AgentTestResponse> {
    const response = await apiClient.post<AgentTestResponse>("/agents/test", payload);
    return response.data;
  }
};


