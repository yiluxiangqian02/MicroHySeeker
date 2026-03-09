import { useState, type FC } from "react";
import type { ControlAgentId } from "@/stores/agentStore";
import { agentsApi } from "@/api/agents";

interface Props {
  agentId: ControlAgentId;
  agentName: string;
}

interface TestResult {
  ok: boolean;
  durationMs: number;
  error?: string;
  result?: Record<string, unknown> | null;
}

export const TestAgentButton: FC<Props> = ({ agentId, agentName }) => {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    const start = Date.now();
    try {
      const res = await agentsApi.test({
        agentId,
        task: { type: "health_check", agent: agentId }
      });
      setTestResult({
        ok: res.ok,
        durationMs: Date.now() - start,
        result: res.result,
        error: res.error ?? undefined
      });
    } catch (e) {
      setTestResult({
        ok: false,
        durationMs: Date.now() - start,
        error: e instanceof Error ? e.message : "请求失败"
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={runTest}
        disabled={testing}
        className="w-full rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {testing ? (
          <span className="flex items-center justify-center gap-1.5">
            <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
            测试中…
          </span>
        ) : (
          `测试 ${agentName} Agent`
        )}
      </button>

      {testResult && (
        <div
          className={`rounded-md px-3 py-2 text-xs ${
            testResult.ok
              ? "bg-emerald-50 text-emerald-700"
              : "bg-red-50 text-red-700"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-medium">
              {testResult.ok ? "✓ 测试通过" : "✗ 测试失败"}
            </span>
            <span className="text-slate-400">{testResult.durationMs}ms</span>
          </div>
          {testResult.error && (
            <p className="mt-1 break-all">{testResult.error}</p>
          )}
          {testResult.ok && testResult.result && (
            <pre className="mt-1 max-h-28 overflow-auto whitespace-pre-wrap break-all text-xs">
              {JSON.stringify(testResult.result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};
