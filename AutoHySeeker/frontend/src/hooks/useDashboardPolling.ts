import { useCallback, useEffect, useState } from "react";
import { healthApi } from "@/api/health";
import { emergencyStop } from "@/api/dashboard";
import { useSettingsStore } from "@/stores/settingsStore";

// ── Hook ──────────────────────────────────────────────────────────────────────
//
// This hook is now a **lightweight health-check + emergency-stop controller**.
// All experiment/agent/chart/log data is sourced from optimizationStore (real API).
// No fake data is generated.

export interface UseDashboardPollingResult {
  /** Whether the backend API is reachable */
  isHealthy: boolean;
  isLoading: boolean;
  pollError: Error | null;
  isStopping: boolean;
  stopError: Error | null;
  stopSuccess: boolean;
  pollingIntervalMs: number;
  lastUpdated: string;
  refresh: () => void;
  requestEmergencyStop: () => Promise<void>;
}

export function useDashboardPolling(): UseDashboardPollingResult {
  const { pollingIntervalMs } = useSettingsStore();

  const [isHealthy, setIsHealthy] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [pollError, setPollError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState(new Date().toISOString());
  const [isStopping, setIsStopping] = useState(false);
  const [stopError, setStopError] = useState<Error | null>(null);
  const [stopSuccess, setStopSuccess] = useState(false);

  const poll = useCallback(async () => {
    try {
      const health = await healthApi.check();
      setIsHealthy(health.status === "ok");
      setPollError(null);
    } catch (e) {
      setIsHealthy(false);
      setPollError(e instanceof Error ? e : new Error("Health check failed"));
    }
    setLastUpdated(new Date().toISOString());
    setIsLoading(false);
  }, []);

  useEffect(() => {
    void poll();
    const id = setInterval(() => { void poll(); }, pollingIntervalMs);
    return () => clearInterval(id);
  }, [poll, pollingIntervalMs]);

  const requestEmergencyStop = useCallback(async () => {
    setIsStopping(true);
    setStopError(null);
    setStopSuccess(false);
    try {
      await emergencyStop();
      setStopSuccess(true);
    } catch (e) {
      setStopError(e instanceof Error ? e : new Error("Emergency stop request failed"));
    } finally {
      setIsStopping(false);
    }
  }, []);

  return {
    isHealthy,
    isLoading,
    pollError,
    isStopping,
    stopError,
    stopSuccess,
    pollingIntervalMs,
    lastUpdated,
    refresh: () => { void poll(); },
    requestEmergencyStop,
  };
}
