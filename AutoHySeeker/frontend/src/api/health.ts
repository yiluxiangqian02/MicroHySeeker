import { apiClient } from "@/api/client";
import type { HealthResponse } from "@/api/types";

export const healthApi = {
  async check(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>("/health");
    return response.data;
  }
};

