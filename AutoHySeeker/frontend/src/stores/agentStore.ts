import { create } from "zustand";
import { agentsApi } from "@/api/agents";
import type {
  AgentId,
  AgentModelConfig,
  AgentModelOption,
  AgentModelsResponse,
  AgentUsageStats,
} from "@/api/types";

export type ControlAgentId = AgentId;

export interface AgentConfig extends AgentModelConfig {
  id: ControlAgentId;
}

export const FALLBACK_AVAILABLE_MODELS: AgentModelOption[] = [
  { value: "anthropic/claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
  { value: "anthropic/claude-opus-4-6", label: "Claude Opus 4.6" },
  { value: "anthropic/claude-haiku-4-5", label: "Claude Haiku 4.5" },
  { value: "ali/qwen3-max-2026-01-23", label: "Qwen3 Max 2026-01-23" },
  { value: "google/gemini-3-flash-preview", label: "Gemini 3 Flash Preview" },
  { value: "bigmodel/GLM-4.6 Thinking", label: "GLM-4.6 Thinking" },
];

export interface AgentDefinition {
  id: ControlAgentId;
  name: string;
  description: string;
  color: "blue" | "red" | "purple" | "green" | "orange";
}

export const AGENT_DEFINITIONS: AgentDefinition[] = [
  {
    id: "orchestrator",
    name: "运行管控 Agent",
    description: "负责全局调度、优化决策和人机协作审批。",
    color: "blue",
  },
  {
    id: "experiment_designer",
    name: "实验设计 Agent",
    description: "负责生成实验方案、策略切换和参数建议。",
    color: "purple",
  },
  {
    id: "experiment_executor",
    name: "实验执行 Agent",
    description: "负责实验执行、状态汇总和监控联动。",
    color: "green",
  },
  {
    id: "diagnostics_expert",
    name: "故障诊断 Agent",
    description: "负责异常排查、原因定位和修复建议。",
    color: "red",
  },
  {
    id: "chat",
    name: "对话 Agent",
    description: "负责统一问答入口、状态查询和知识检索。",
    color: "orange",
  },
  {
    id: "heartbeat_inspector",
    name: "心跳巡检",
    description: "负责 L2 心跳巡检和周期性风险复核。",
    color: "green",
  },
];

const CONTROL_AGENT_IDS: ControlAgentId[] = AGENT_DEFINITIONS.map((definition) => definition.id);

const buildDefaultConfig = (id: ControlAgentId): AgentConfig => ({
  id,
  enabled: true,
  primaryModel: "anthropic/claude-sonnet-4-6",
  fallbackModel: "anthropic/claude-opus-4-6",
  apiKey: "",
  baseUrl: "https://api.mcxhm.cn",
  temperature: 0.2,
  maxTokens: null,
  displayName: AGENT_DEFINITIONS.find((definition) => definition.id === id)?.name ?? id,
});

const DEFAULT_CONFIGS = Object.fromEntries(
  CONTROL_AGENT_IDS.map((id) => [id, buildDefaultConfig(id)]),
) as Record<ControlAgentId, AgentConfig>;

const DEFAULT_USAGE = Object.fromEntries(
  CONTROL_AGENT_IDS.map((id) => [
    id,
    { inputTokens: 0, outputTokens: 0, estimatedCostUsd: 0 } satisfies AgentUsageStats,
  ]),
) as Record<ControlAgentId, AgentUsageStats>;

const toAgentConfig = (
  id: ControlAgentId,
  payload: NonNullable<AgentModelsResponse["agents"][ControlAgentId]>,
): AgentConfig => ({
  id,
  enabled: payload.enabled,
  primaryModel: payload.primary_model,
  fallbackModel: payload.fallback_model,
  apiKey: payload.api_key,
  baseUrl: payload.base_url,
  temperature: payload.temperature,
  maxTokens: payload.max_tokens,
  displayName: payload.display_name,
});

interface AgentControlStore {
  configs: Record<ControlAgentId, AgentConfig>;
  usage: Record<ControlAgentId, AgentUsageStats>;
  availableModels: AgentModelOption[];
  defaults: {
    model: string;
    fallbackModel: string;
    baseUrl: string;
  };
  loading: boolean;
  loaded: boolean;
  error: string | null;
  setConfig: (id: ControlAgentId, update: Partial<AgentModelConfig>) => void;
  loadConfigs: () => Promise<void>;
  saveConfig: (id: ControlAgentId) => Promise<void>;
  setAllEnabled: (enabled: boolean) => void;
  resetAll: () => void;
  updateUsage: (id: ControlAgentId, usage: Partial<AgentUsageStats>) => void;
  importConfigs: (configs: Partial<Record<ControlAgentId, AgentConfig>>) => void;
}

export const useAgentStore = create<AgentControlStore>((set, get) => ({
  configs: DEFAULT_CONFIGS,
  usage: DEFAULT_USAGE,
  availableModels: FALLBACK_AVAILABLE_MODELS,
  defaults: {
    model: "anthropic/claude-sonnet-4-6",
    fallbackModel: "anthropic/claude-opus-4-6",
    baseUrl: "https://api.mcxhm.cn",
  },
  loading: false,
  loaded: false,
  error: null,

  setConfig: (id, update) =>
    set((state) => ({
      configs: { ...state.configs, [id]: { ...state.configs[id], ...update } },
    })),

  loadConfigs: async () => {
    set({ loading: true, error: null });
    try {
      const response = await agentsApi.getModels();
      const nextConfigs = { ...DEFAULT_CONFIGS };
      for (const id of CONTROL_AGENT_IDS) {
        const payload = response.agents[id];
        if (payload) {
          nextConfigs[id] = toAgentConfig(id, payload);
        }
      }
      set({
        configs: nextConfigs,
        availableModels: response.available_models.length
          ? response.available_models
          : FALLBACK_AVAILABLE_MODELS,
        defaults: {
          model: response.defaults.model,
          fallbackModel: response.defaults.fallback_model,
          baseUrl: response.defaults.base_url,
        },
        loading: false,
        loaded: true,
        error: null,
      });
    } catch (error) {
      set({
        loading: false,
        loaded: true,
        error: error instanceof Error ? error.message : "加载 Agent 配置失败",
      });
      throw error;
    }
  },

  saveConfig: async (id) => {
    const config = get().configs[id];
    const response = await agentsApi.updateModelConfig(id, {
      enabled: config.enabled,
      primary_model: config.primaryModel,
      fallback_model: config.fallbackModel,
      api_key: config.apiKey,
      temperature: config.temperature,
      max_tokens: config.maxTokens ?? null,
      base_url: config.baseUrl,
    });
    set((state) => ({
      configs: {
        ...state.configs,
        [id]: toAgentConfig(id, response.agent),
      },
    }));
  },

  setAllEnabled: (enabled) =>
    set((state) => ({
      configs: Object.fromEntries(
        Object.entries(state.configs).map(([key, value]) => [key, { ...value, enabled }]),
      ) as Record<ControlAgentId, AgentConfig>,
    })),

  resetAll: () =>
    set((state) => ({
      configs: Object.fromEntries(
        Object.entries(state.configs).map(([key, value]) => [
          key,
          {
            ...value,
            enabled: true,
            primaryModel: state.defaults.model,
            fallbackModel: state.defaults.fallbackModel,
            baseUrl: state.defaults.baseUrl,
          },
        ]),
      ) as Record<ControlAgentId, AgentConfig>,
    })),

  updateUsage: (id, usage) =>
    set((state) => ({
      usage: { ...state.usage, [id]: { ...state.usage[id], ...usage } },
    })),

  importConfigs: (incoming) =>
    set((state) => ({
      configs: Object.fromEntries(
        Object.entries({
          ...state.configs,
          ...incoming,
        }).map(([key, value]) => [
          key,
          {
            ...buildDefaultConfig(key as ControlAgentId),
            ...value,
          },
        ]),
      ) as Record<ControlAgentId, AgentConfig>,
    })),
}));
