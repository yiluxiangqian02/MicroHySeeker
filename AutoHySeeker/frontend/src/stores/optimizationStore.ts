import { create } from "zustand";
import {
  OptimizationConfig,
  OptimizationState,
  mapOptimizationConfig,
  mapOptimizationState,
  optimizationApi,
} from "@/api/optimization";

interface OptimizationStore {
  config: OptimizationConfig | null;
  state: OptimizationState | null;
  isLoading: boolean;
  error: string | null;
  fetchConfigAndState: () => Promise<void>;
  startLoop: () => Promise<void>;
  stopLoop: () => Promise<void>;
  resetLoop: () => Promise<void>;
}

export const useOptimizationStore = create<OptimizationStore>((set, get) => ({
  config: null,
  state: null,
  isLoading: false,
  error: null,

  fetchConfigAndState: async () => {
    set({ isLoading: true, error: null });
    try {
      const [status, history] = await Promise.all([
        optimizationApi.getStatus(),
        optimizationApi.getHistory(),
      ]);

      set({
        config: mapOptimizationConfig(status),
        state: mapOptimizationState(status, history),
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch optimization data",
        isLoading: false,
      });
      throw error;
    }
  },

  startLoop: async () => {
    set({ isLoading: true, error: null });
    try {
      const currentConfig = get().config;
      await optimizationApi.start({
        goal: currentConfig?.goal || "Optimize experiment loop",
        max_rounds: currentConfig?.maxIterations || 10,
        target_metric: currentConfig?.targetMetric || "overpotential_mV",
        direction: currentConfig?.direction || "minimize",
        template_id: currentConfig?.templateId || "tpl_her_standard",
        elements: currentConfig?.elements || ["Fe", "Co", "Ni"],
        dry_run: false,
      });
      await get().fetchConfigAndState();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to start optimization loop",
        isLoading: false,
      });
      throw error;
    }
  },

  stopLoop: async () => {
    set({ isLoading: true, error: null });
    try {
      await optimizationApi.stop();
      await get().fetchConfigAndState();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to stop optimization loop",
        isLoading: false,
      });
      throw error;
    }
  },

  resetLoop: async () => {
    set({ isLoading: true, error: null });
    try {
      await optimizationApi.reset();
      await get().fetchConfigAndState();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to reset optimization loop",
        isLoading: false,
      });
      throw error;
    }
  },
}));
