import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AgentUsageStats, AgentModelConfig } from "@/api/types";

/** The 5 configurable agents in the control panel */
export type ControlAgentId = "C1" | "C2" | "C3" | "D2" | "D3";

export interface AgentConfig extends AgentModelConfig {
  id: ControlAgentId;
}

export const AVAILABLE_MODELS = [
  { value: "claude-opus-4.6", label: "Claude Opus 4.6" },
  { value: "claude-sonnet-4.6", label: "Claude Sonnet 4.6" },
  { value: "claude-haiku-4.5", label: "Claude Haiku 4.5" },
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "rule-based", label: "Rule-based (无 LLM)" },
] as const;

export interface AgentDefinition {
  id: ControlAgentId;
  name: string;
  description: string;
  color: "blue" | "red" | "purple" | "green" | "orange";
}

export const AGENT_DEFINITIONS: AgentDefinition[] = [
  {
    id: "C1",
    name: "数据解读助手",
    description: "适合在实验结束后查看结果、提取关键指标、比较多组数据时使用",
    color: "blue"
  },
  {
    id: "D2",
    name: "故障排查助手",
    description: "适合实验失败、曲线异常、设备状态不对时帮助定位原因和排查路径",
    color: "red"
  },
  {
    id: "D3",
    name: "方案设计助手",
    description: "适合在开始实验前补齐参数、生成起始方案、获得下一轮实验建议时使用",
    color: "purple"
  },
  {
    id: "C2",
    name: "运行监护助手",
    description: "适合在实验执行过程中盯住进展、异常和关键节点，减少人工盯屏",
    color: "green"
  },
  {
    id: "C3",
    name: "知识检索助手",
    description: "适合回看历史实验、方法经验和知识背景，帮助快速找到可复用信息",
    color: "orange"
  }
];

const CONTROL_AGENT_IDS: ControlAgentId[] = ["C1", "D2", "D3", "C2", "C3"];

const DEFAULT_CONFIGS = Object.fromEntries(
  CONTROL_AGENT_IDS.map((id) => [
    id,
    {
      id,
      enabled: true,
      primaryModel: "claude-sonnet-4.6",
      fallbackModel: "rule-based",
      apiKey: ""
    } satisfies AgentConfig
  ])
) as Record<ControlAgentId, AgentConfig>;

const DEFAULT_USAGE = Object.fromEntries(
  CONTROL_AGENT_IDS.map((id) => [
    id,
    { inputTokens: 0, outputTokens: 0, estimatedCostUsd: 0 } satisfies AgentUsageStats
  ])
) as Record<ControlAgentId, AgentUsageStats>;

interface AgentControlStore {
  configs: Record<ControlAgentId, AgentConfig>;
  usage: Record<ControlAgentId, AgentUsageStats>;
  setConfig: (id: ControlAgentId, update: Partial<AgentModelConfig>) => void;
  setAllEnabled: (enabled: boolean) => void;
  resetAll: () => void;
  updateUsage: (id: ControlAgentId, usage: Partial<AgentUsageStats>) => void;
  importConfigs: (configs: Partial<Record<ControlAgentId, AgentConfig>>) => void;
}

export const useAgentStore = create<AgentControlStore>()(
  persist(
    (set) => ({
      configs: DEFAULT_CONFIGS,
      usage: DEFAULT_USAGE,

      setConfig: (id, update) =>
        set((state) => ({
          configs: { ...state.configs, [id]: { ...state.configs[id], ...update } }
        })),

      setAllEnabled: (enabled) =>
        set((state) => ({
          configs: Object.fromEntries(
            Object.entries(state.configs).map(([k, v]) => [k, { ...v, enabled }])
          ) as Record<ControlAgentId, AgentConfig>
        })),

      resetAll: () => set({ configs: DEFAULT_CONFIGS }),

      updateUsage: (id, usage) =>
        set((state) => ({
          usage: { ...state.usage, [id]: { ...state.usage[id], ...usage } }
        })),

      importConfigs: (incoming) =>
        set((state) => ({
          configs: { ...state.configs, ...incoming }
        }))
    }),
    {
      name: "autohyseeker-agent-control",
      partialize: (state) => ({ configs: state.configs })
    }
  )
);
