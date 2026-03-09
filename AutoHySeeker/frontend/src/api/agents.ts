import { apiClient } from "@/api/client";
import type { AgentInvokeRequest, AgentInvokeResponse } from "@/api/types";

export const agentsApi = {
  async invoke(payload: AgentInvokeRequest): Promise<AgentInvokeResponse> {
    const response = await apiClient.post<AgentInvokeResponse>("/agents/invoke", payload);
    return response.data;
  }
};

