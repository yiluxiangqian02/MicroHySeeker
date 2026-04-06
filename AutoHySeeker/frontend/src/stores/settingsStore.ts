import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AppSettings {
  apiBaseUrl: string;
  defaultDiagnosticsDataDir: string;
  defaultContextHistoryDir: string;
  pollingIntervalMs: number;
  requestTimeoutMs: number;
}

export const DEFAULT_SETTINGS: AppSettings = {
  apiBaseUrl: "",
  defaultDiagnosticsDataDir: "",
  defaultContextHistoryDir: "",
  pollingIntervalMs: 5000,
  requestTimeoutMs: 30000
};

interface SettingsStore extends AppSettings {
  setSettings: (next: Partial<AppSettings>) => void;
  resetSettings: () => void;
}

export const useSettingsStore = create<SettingsStore>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,
      setSettings: (next) => set((state) => ({ ...state, ...next })),
      resetSettings: () => set(DEFAULT_SETTINGS)
    }),
    {
      name: "autohyseeker-settings",
      version: 1,
      partialize: (state) => ({
        apiBaseUrl: state.apiBaseUrl,
        defaultDiagnosticsDataDir: state.defaultDiagnosticsDataDir,
        defaultContextHistoryDir: state.defaultContextHistoryDir,
        pollingIntervalMs: state.pollingIntervalMs,
        requestTimeoutMs: state.requestTimeoutMs
      }),
      migrate: (persisted: unknown, version: number) => {
        const state = persisted as Record<string, unknown>;
        if (version === 0) {
          // Clear stale hardcoded API URL from previous versions
          const url = state.apiBaseUrl as string | undefined;
          if (url && url.includes("localhost:8100")) {
            state.apiBaseUrl = "";
          }
        }
        return state as unknown as AppSettings;
      }
    }
  )
);

