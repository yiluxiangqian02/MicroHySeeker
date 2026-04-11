/**
 * 全局系统配置 store — 启动时自动从后端预加载泵/通道配置，
 * 避免每次打开创建对话框时重新请求。
 */
import { create } from "zustand";

export interface PumpCfg {
  address: number;
  name: string;
  direction: string;
  default_rpm: number;
}

export interface DilutionChannel {
  channel_id: string;
  solution_name: string;
  stock_concentration: number;
  pump_address: number;
  direction: string;
  default_rpm: number;
  color?: string;
  tube_diameter_mm?: number;
  total_volume_ml?: number;
  remaining_volume_ml?: number;
}

export interface FlushChannelCfg {
  channel_id: string;
  pump_name: string;
  pump_address: number;
  direction: string;
  rpm: number;
  cycle_duration_s: number;
  work_type: string;
  tube_diameter_mm?: number;
  total_volume_ml?: number | null;
}

export interface SystemConfig {
  pumps: PumpCfg[];
  dilution_channels: DilutionChannel[];
  flush_channels: FlushChannelCfg[];
}

interface MHSStatus {
  online: boolean;
  connected: boolean;
  mock_mode: boolean;
}

interface SystemConfigStore {
  /** 硬件配置 */
  config: SystemConfig | null;
  /** MHS 连接状态 */
  mhsStatus: MHSStatus;
  /** 加载状态 */
  loading: boolean;
  /** 上次成功加载时间 */
  lastFetchedAt: number | null;
  /** 错误信息 */
  error: string | null;

  /** 从后端拉取最新配置 */
  fetchConfig: () => Promise<void>;
  /** 同时拉取 MHS 状态 */
  fetchMHSStatus: () => Promise<void>;
  /** 一次性初始化（配置 + 状态） */
  init: () => Promise<void>;
}

export const useSystemConfigStore = create<SystemConfigStore>()((set, get) => ({
  config: null,
  mhsStatus: { online: false, connected: false, mock_mode: true },
  loading: false,
  lastFetchedAt: null,
  error: null,

  fetchConfig: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await fetch("/api/system/config");
      if (resp.ok) {
        const data: SystemConfig = await resp.json();
        set({ config: data, lastFetchedAt: Date.now(), loading: false });
      } else {
        set({ error: `HTTP ${resp.status}`, loading: false });
      }
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },

  fetchMHSStatus: async () => {
    try {
      const resp = await fetch("/api/system/status");
      if (resp.ok) {
        const data = await resp.json();
        const mhs = data.mhs ?? data.microhyseeker ?? {};
        set({
          mhsStatus: {
            online: mhs.online ?? false,
            connected: mhs.rs485_connected ?? false,
            mock_mode: mhs.mock_mode ?? true,
          },
        });
      }
    } catch {
      set({ mhsStatus: { online: false, connected: false, mock_mode: true } });
    }
  },

  init: async () => {
    const state = get();
    // 避免重复初始化（5 分钟内有效）
    if (state.config && state.lastFetchedAt && Date.now() - state.lastFetchedAt < 300_000) {
      return;
    }
    await Promise.all([get().fetchConfig(), get().fetchMHSStatus()]);
  },
}));
