import { useRef, type ChangeEvent } from "react";
import { AGENT_DEFINITIONS, useAgentStore } from "@/stores/agentStore";
import type { AgentConfig, ControlAgentId } from "@/stores/agentStore";
import { AgentCard } from "@/components/AgentCard";

export function AgentControl() {
  const configs = useAgentStore((s) => s.configs);
  const setAllEnabled = useAgentStore((s) => s.setAllEnabled);
  const resetAll = useAgentStore((s) => s.resetAll);
  const importConfigs = useAgentStore((s) => s.importConfigs);
  const importRef = useRef<HTMLInputElement>(null);

  const enabledCount = Object.values(configs).filter((c) => c.enabled).length;
  const totalCount = AGENT_DEFINITIONS.length;

  const handleExport = () => {
    const data = JSON.stringify(configs, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agent-configs-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string) as Partial<
          Record<ControlAgentId, AgentConfig>
        >;
        importConfigs(parsed);
      } catch {
        alert("配置文件格式无效，请导入合法的 JSON 文件。");
      }
    };
    reader.readAsText(file);
    // Reset input so same file can be re-imported
    e.target.value = "";
  };

  const handleResetAll = () => {
    if (window.confirm("确定重置所有 Agent 配置为默认值吗？此操作不可撤销。")) {
      resetAll();
    }
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Agent 控制台</h2>
          <p className="mt-1 text-sm text-slate-500">
            配置和管理各 Agent 的模型、API Key 及运行参数
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {enabledCount}/{totalCount} 个 Agent 已启用
          </p>
        </div>

        {/* Bulk operations */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setAllEnabled(true)}
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
          >
            全部启用
          </button>
          <button
            onClick={() => setAllEnabled(false)}
            className="rounded-md bg-slate-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-600"
          >
            全部禁用
          </button>
          <button
            onClick={handleResetAll}
            className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
          >
            重置所有配置
          </button>
          <button
            onClick={handleExport}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            导出配置
          </button>
          <button
            onClick={() => importRef.current?.click()}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            导入配置
          </button>
          <input
            ref={importRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={handleImportFile}
          />
        </div>
      </div>

      {/* Status summary bar */}
      <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        {AGENT_DEFINITIONS.map((def) => {
          const cfg = configs[def.id];
          return (
            <div
              key={def.id}
              className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1"
            >
              <span
                className={`inline-block h-2 w-2 rounded-full ${cfg?.enabled ? "bg-emerald-400" : "bg-slate-300"}`}
              />
              <span className="text-xs font-medium text-slate-700">
                {def.id}
              </span>
              <span className="text-xs text-slate-400">{def.name}</span>
            </div>
          );
        })}
      </div>

      {/* Agent cards grid */}
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        {AGENT_DEFINITIONS.map((def) => (
          <AgentCard key={def.id} definition={def} />
        ))}
      </div>
    </div>
  );
}
