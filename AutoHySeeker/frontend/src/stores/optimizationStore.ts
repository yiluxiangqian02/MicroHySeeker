import { create } from "zustand";
import { optimizationApi, OptimizationConfig, OptimizationState } from "@/api/optimization";

// Default Mock Data for development UI testing
const MOCK_CONFIG: OptimizationConfig = {
  targetFunction: "maximize_yield",
  parameterSpace: {
    "flow_rate": { type: "continuous", min: 10, max: 100 },
    "temperature": { type: "continuous", min: 20, max: 80 },
    "catalyst_ratio": { type: "continuous", min: 0.1, max: 5.0 }
  },
  constraints: ["flow_rate * temperature < 5000", "catalyst_ratio > 0.5"],
  maxIterations: 20
};

const MOCK_STATE: OptimizationState = {
  status: "running",
  currentIteration: 5,
  maxIterations: 20,
  bestYield: 86.4,
  bestParams: {
    flow_rate: 45.5,
    temperature: 65,
    catalyst_ratio: 1.2
  },
  history: [
    { iteration: 1, yield: 45.2, params: { flow_rate: 20, temperature: 30, catalyst_ratio: 1.0 } },
    { iteration: 2, yield: 58.7, params: { flow_rate: 30, temperature: 40, catalyst_ratio: 1.0 } },
    { iteration: 3, yield: 72.1, params: { flow_rate: 40, temperature: 55, catalyst_ratio: 1.1 } },
    { iteration: 4, yield: 82.5, params: { flow_rate: 45, temperature: 60, catalyst_ratio: 1.15 } },
    { iteration: 5, yield: 86.4, params: { flow_rate: 45.5, temperature: 65, catalyst_ratio: 1.2 } },
  ],
  nextSuggestion: {
    reason: "Gradient ascent indicates higher temperature might further improve yield within safe bounds.",
    suggestedParams: { flow_rate: 46.0, temperature: 68, catalyst_ratio: 1.25 },
    predictedYield: 88.1
  }
};

interface OptimizationStore {
  config: OptimizationConfig | null;
  state: OptimizationState | null;
  isLoading: boolean;
  error: string | null;
  fetchConfigAndState: () => Promise<void>;
  updateConfig: (config: OptimizationConfig) => Promise<void>;
  startLoop: () => Promise<void>;
  stopLoop: () => Promise<void>;
}

export const useOptimizationStore = create<OptimizationStore>((set, get) => ({
  config: null,
  state: null,
  isLoading: false,
  error: null,

  fetchConfigAndState: async () => {
    set({ isLoading: true, error: null });
    try {
      // Temporary: Use mock data directly since P1-15 backend is not yet available
      // const config = await optimizationApi.getConfig();
      // const state = await optimizationApi.getState();
      
      // Simulate network delay
      await new Promise(resolve => setTimeout(resolve, 600));
      
      set({ 
        config: MOCK_CONFIG, 
        state: MOCK_STATE, 
        isLoading: false 
      });
    } catch (err: any) {
      set({ error: err.message || "Failed to fetch optimization data", isLoading: false });
    }
  },

  updateConfig: async (newConfig) => {
    set({ isLoading: true, error: null });
    try {
      // await optimizationApi.updateConfig(newConfig);
      await new Promise(resolve => setTimeout(resolve, 400));
      set({ config: newConfig, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || "Failed to update config", isLoading: false });
    }
  },

  startLoop: async () => {
    set({ isLoading: true, error: null });
    try {
      // await optimizationApi.start();
      await new Promise(resolve => setTimeout(resolve, 400));
      const currentState = get().state;
      if (currentState) {
        set({ state: { ...currentState, status: "running" }, isLoading: false });
      }
    } catch (err: any) {
      set({ error: err.message || "Failed to start optimization loop", isLoading: false });
    }
  },

  stopLoop: async () => {
    set({ isLoading: true, error: null });
    try {
      // await optimizationApi.stop();
      await new Promise(resolve => setTimeout(resolve, 400));
      const currentState = get().state;
      if (currentState) {
        set({ state: { ...currentState, status: "paused" }, isLoading: false });
      }
    } catch (err: any) {
      set({ error: err.message || "Failed to stop optimization loop", isLoading: false });
    }
  }
}));
