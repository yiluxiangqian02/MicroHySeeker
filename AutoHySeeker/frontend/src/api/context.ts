import { apiClient } from "@/api/client";
import type { ContextInvokeRequest, ContextResponse } from "@/api/types";

export const contextApi = {
  async invoke(payload: ContextInvokeRequest): Promise<ContextResponse> {
    const response = await apiClient.post<ContextResponse>("/context/invoke", payload);
    return response.data;
  },

  async contextualize(payload: Omit<ContextInvokeRequest, "action">): Promise<ContextResponse> {
    return contextApi.invoke({ ...payload, action: "contextualize" });
  },

  async suggest(payload: Omit<ContextInvokeRequest, "action">): Promise<ContextResponse> {
    return contextApi.invoke({ ...payload, action: "suggest" });
  }
};

