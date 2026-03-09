import type { FC } from "react";
import type { AgentUsageStats } from "@/api/types";

interface Props {
  stats: AgentUsageStats;
  onReset?: () => void;
}

export const UsageStats: FC<Props> = ({ stats, onReset }) => {
  const totalTokens = stats.inputTokens + stats.outputTokens;

  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-xs text-slate-500">输入 Tokens</p>
          <p className="mt-0.5 text-sm font-semibold text-slate-800">
            {stats.inputTokens.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">输出 Tokens</p>
          <p className="mt-0.5 text-sm font-semibold text-slate-800">
            {stats.outputTokens.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-500">预估费用</p>
          <p className="mt-0.5 text-sm font-semibold text-slate-800">
            ${stats.estimatedCostUsd.toFixed(4)}
          </p>
        </div>
      </div>
      {totalTokens > 0 && (
        <div className="mt-2 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            合计 {totalTokens.toLocaleString()} tokens
          </p>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="text-xs text-slate-400 hover:text-slate-600 underline"
            >
              重置统计
            </button>
          )}
        </div>
      )}
    </div>
  );
};
