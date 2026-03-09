import { apiClient } from "./client";
import type { EmergencyStopResponse } from "./types";

/**
 * POST /control/stop
 * Sends an emergency stop signal to the backend.
 * The endpoint may not be available yet; callers should handle the error.
 */
export async function emergencyStop(): Promise<EmergencyStopResponse> {
  const response = await apiClient.post<EmergencyStopResponse>("/control/stop");
  return response.data;
}
