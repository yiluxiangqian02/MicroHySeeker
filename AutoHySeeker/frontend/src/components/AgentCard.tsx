import { useEffect, useState, type FC } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { AgentDefinition } from "@/stores/agentStore";
import { useAgentStore } from "@/stores/agentStore";
import type { AgentStatus } from "@/api/types";
import { agentsApi } from "@/api/agents";
import { ModelSelector } from "@/components/ModelSelector";
import { ApiKeyInput } from "@/components/ApiKeyInput";
import { UsageStats } from "@/components/UsageStats";
import { TestAgentButton } from "@/components/TestAgentButton";

const cardSchema = z.object({
  enabled: z.boolean(),
  primaryModel: z.string().min(1, "请选择主模型"),
  fallbackModel: z.string().min(1, "请选择降级模型"),
  apiKey: z.string()
});

type CardFormValues = z.infer<typeof cardSchema>;

const STATUS_STYLES: Record<AgentStatus, { dot: string; text: string; label: string }> = {
  idle: { dot: "bg-slate-300", text: "text-slate-500", label: "空闲" },
  working: { dot: "bg-amber-400 animate-pulse", text: "text-amber-600", label: "运行中" },
  error: { dot: "bg-red-500", text: "text-red-600", label: "错误" }
};

const CARD_STYLES: Record<string, { border: string; badge: string; header: string }> = {
  blue: {
    border: "border-blue-200",
    badge: "bg-blue-100 text-blue-800",
    header: "from-blue-50 to-white"
  },
  red: {
    border: "border-red-200",
    badge: "bg-red-100 text-red-800",
    header: "from-red-50 to-white"
  },
  purple: {
    border: "border-purple-200",
    badge: "bg-purple-100 text-purple-800",
    header: "from-purple-50 to-white"
  },
  green: {
    border: "border-green-200",
    badge: "bg-green-100 text-green-800",
    header: "from-green-50 to-white"
  },
  orange: {
    border: "border-orange-200",
    badge: "bg-orange-100 text-orange-800",
    header: "from-orange-50 to-white"
  }
};

interface Props {
  definition: AgentDefinition;
  status?: AgentStatus;
}

export const AgentCard: FC<Props> = ({ definition, status = "idle" }) => {
  const config = useAgentStore((s) => s.configs[definition.id]);
  const usage = useAgentStore((s) => s.usage[definition.id]);
  const setConfig = useAgentStore((s) => s.setConfig);
  const updateUsage = useAgentStore((s) => s.updateUsage);

  const [saveState, setSaveState] = useState<{
    type: "success" | "error";
    msg: string;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty }
  } = useForm<CardFormValues>({
    resolver: zodResolver(cardSchema),
    defaultValues: {
      enabled: config.enabled,
      primaryModel: config.primaryModel,
      fallbackModel: config.fallbackModel,
      apiKey: config.apiKey
    }
  });

  // Sync form when store config changes externally (bulk enable/disable/reset)
  useEffect(() => {
    reset({
      enabled: config.enabled,
      primaryModel: config.primaryModel,
      fallbackModel: config.fallbackModel,
      apiKey: config.apiKey
    });
  }, [config.enabled, config.primaryModel, config.fallbackModel, config.apiKey, reset]);

  const onSubmit = async (values: CardFormValues) => {
    setSaving(true);
    setSaveState(null);
    setConfig(definition.id, values);
    try {
      await agentsApi.saveConfig({ agentId: definition.id, config: values });
      setSaveState({ type: "success", msg: "配置已保存至服务端" });
    } catch {
      // Local store already updated; treat as partial success
      setSaveState({ type: "success", msg: "配置已保存（本地）" });
    } finally {
      setSaving(false);
    }
  };

  const handleResetUsage = () => {
    updateUsage(definition.id, { inputTokens: 0, outputTokens: 0, estimatedCostUsd: 0 });
  };

  const cardStyle = CARD_STYLES[definition.color] ?? CARD_STYLES.blue;
  const statusStyle = STATUS_STYLES[status];

  return (
    <div
      className={`flex flex-col rounded-xl border ${cardStyle.border} bg-white shadow-sm overflow-hidden`}
    >
      {/* Header */}
      <div className={`bg-gradient-to-b ${cardStyle.header} px-5 py-4`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={`inline-block rounded-md px-2 py-0.5 text-xs font-bold tracking-wider ${cardStyle.badge}`}
            >
              {definition.id}
            </span>
            <h3 className="text-base font-semibold text-slate-900">
              {definition.name}
            </h3>
          </div>

          {/* Status badge */}
          <div className="flex shrink-0 items-center gap-1.5">
            <span
              className={`inline-block h-2 w-2 rounded-full ${statusStyle.dot}`}
            />
            <span className={`text-xs font-medium ${statusStyle.text}`}>
              {statusStyle.label}
            </span>
          </div>
        </div>
        <p className="mt-1 text-sm text-slate-500">{definition.description}</p>
      </div>

      {/* Form body */}
      <form
        className="flex flex-1 flex-col gap-4 px-5 py-4"
        onSubmit={handleSubmit(onSubmit)}
      >
        {/* Enable toggle */}
        <label className="flex cursor-pointer items-center gap-2">
          <input
            {...register("enabled")}
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-slate-700">启用此 Agent</span>
        </label>

        {/* Model selectors */}
        <div className="grid gap-3 sm:grid-cols-2">
          <Controller
            name="primaryModel"
            control={control}
            render={({ field }) => (
              <ModelSelector
                id={`primary-${definition.id}`}
                label="主模型"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
          <Controller
            name="fallbackModel"
            control={control}
            render={({ field }) => (
              <ModelSelector
                id={`fallback-${definition.id}`}
                label="降级模型"
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </div>
        {(errors.primaryModel ?? errors.fallbackModel) && (
          <p className="text-xs text-red-600">
            {errors.primaryModel?.message ?? errors.fallbackModel?.message}
          </p>
        )}

        {/* API Key */}
        <Controller
          name="apiKey"
          control={control}
          render={({ field }) => (
            <ApiKeyInput
              id={`apikey-${definition.id}`}
              value={field.value}
              onChange={field.onChange}
            />
          )}
        />

        {/* Save notice */}
        {saveState && (
          <p
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
              saveState.type === "success"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {saveState.type === "success" ? "✓ " : "✗ "}
            {saveState.msg}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saving || !isDirty}
            className="flex-1 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "保存中…" : "保存配置"}
          </button>
          <button
            type="button"
            onClick={() => reset()}
            disabled={!isDirty}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            还原
          </button>
        </div>
      </form>

      {/* Usage stats + test */}
      <div className="border-t border-slate-100 px-5 py-4 space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          使用量统计
        </h4>
        <UsageStats stats={usage} onReset={handleResetUsage} />
        <TestAgentButton agentId={definition.id} agentName={definition.name} />
      </div>
    </div>
  );
};
