import { apiClient } from "@/api/client";
import type {
  AgentInvokeRequest,
  AgentInvokeResponse,
  AgentConfigSaveRequest,
  AgentConfigSaveResponse,
  AgentModelsResponse,
  AgentModelUpdateRequest,
  AgentModelUpdateResponse,
  AgentTestRequest,
  AgentTestResponse
} from "@/api/types";

export const agentsApi = {
  async invoke(payload: AgentInvokeRequest): Promise<AgentInvokeResponse> {
    const response = await apiClient.post<AgentInvokeResponse>("/agents/invoke", payload);
    return response.data;
  },

  async saveConfig(payload: AgentConfigSaveRequest): Promise<AgentConfigSaveResponse> {
    const response = await apiClient.put<AgentModelUpdateResponse>(
      `/api/agents/models/${payload.agentId}`,
      {
        enabled: payload.config.enabled,
        primary_model: payload.config.primaryModel,
        fallback_model: payload.config.fallbackModel,
        api_key: payload.config.apiKey,
        temperature: payload.config.temperature,
        max_tokens: payload.config.maxTokens,
        base_url: payload.config.baseUrl
      } satisfies AgentModelUpdateRequest,
    );
    return { ok: response.data.ok };
  },

  async getModels(): Promise<AgentModelsResponse> {
    const response = await apiClient.get<AgentModelsResponse>("/api/agents/models");
    return response.data;
  },

  async updateModelConfig(
    agentId: AgentConfigSaveRequest["agentId"],
    payload: AgentModelUpdateRequest,
  ): Promise<AgentModelUpdateResponse> {
    const response = await apiClient.put<AgentModelUpdateResponse>(
      `/api/agents/models/${agentId}`,
      payload,
    );
    return response.data;
  },

  async test(payload: AgentTestRequest): Promise<AgentTestResponse> {
    const response = await apiClient.post<AgentInvokeResponse>("/agents/invoke", {
      task: payload.task ?? { type: "health_check", agent: payload.agentId },
      current_agent: payload.agentId
    });
    return {
      ok: response.data.ok,
      agentId: payload.agentId,
      result: response.data.result,
      error: response.data.ok ? null : "Agent invocation failed"
    };
  }
};

