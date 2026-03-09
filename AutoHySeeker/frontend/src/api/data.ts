import { apiClient } from "@/api/client";
import type { ExperimentsResponse, LatestExperimentResponse } from "@/api/types";

export const dataApi = {
  async listExperiments(limit = 10): Promise<ExperimentsResponse> {
    const response = await apiClient.get<ExperimentsResponse>("/data/experiments", {
      params: { limit }
    });
    return response.data;
  },

  async getLatestExperiment(): Promise<LatestExperimentResponse> {
    const response = await apiClient.get<LatestExperimentResponse>("/data/latest");
    return response.data;
  }
};

