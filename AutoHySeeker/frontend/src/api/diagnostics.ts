import { apiClient } from "@/api/client";
import type { DiagnosticsInvokeRequest, DiagnosticsResponse } from "@/api/types";

export const diagnosticsApi = {
  async invoke(payload: DiagnosticsInvokeRequest): Promise<DiagnosticsResponse> {
    const response = await apiClient.post<DiagnosticsResponse>("/diagnostics/invoke", payload);
    return response.data;
  },

  async analyzeFailure(
    runDir: string,
    context: Record<string, unknown> = {}
  ): Promise<DiagnosticsResponse> {
    return diagnosticsApi.invoke({
      action: "analyze_failure",
      run_dir: runDir,
      context
    });
  },

  async checkHealth(
    dataDir: string,
    recentN = 10,
    context: Record<string, unknown> = {}
  ): Promise<DiagnosticsResponse> {
    return diagnosticsApi.invoke({
      action: "check_health",
      data_dir: dataDir,
      recent_n: recentN,
      context
    });
  }
};

