import { useTranslation } from "react-i18next";
import { useEffect, useRef, useState, useCallback } from "react";
import { useOptimizationStore } from "@/stores/optimizationStore";
import { experimentsApi } from "@/api/experiments";
import { Play, Square, Settings as SettingsIcon, BrainCircuit, RefreshCw, Trophy, FlaskConical, Target, AlertCircle, CheckCircle2, RotateCcw, Download, X, Beaker } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import toast from "react-hot-toast";

export function Optimization() {
  const { t } = useTranslation();
  const { config, state, isLoading, fetchConfigAndState, startLoop, stopLoop, resetLoop } = useOptimizationStore();
  const [showCompletionDialog, setShowCompletionDialog] = useState(false);
  const prevStatusRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    const refreshStatus = () => {
      fetchConfigAndState().catch(() => undefined);
    };

    refreshStatus();
    const timer = window.setInterval(() => {
      refreshStatus();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [fetchConfigAndState]);

  // Detect optimization completion / stop → show dialog
  useEffect(() => {
    const currentStatus = state?.status;
    const prev = prevStatusRef.current;
    if (
      prev &&
      prev !== currentStatus &&
      (prev === "running" || prev === "executing" || prev === "designing" || prev === "analyzing" || prev === "evaluating") &&
      (currentStatus === "completed" || currentStatus === "stopped" || currentStatus === "error")
    ) {
      setShowCompletionDialog(true);
    }
    prevStatusRef.current = currentStatus;
  }, [state?.status]);

  const handleStartLoop = async () => {
    try {
      await startLoop();
      toast.success(t('optimization.start_loop'));
    } catch {
      toast.error(t('optimization.failed'));
    }
  };

  const handleStopLoop = async () => {
    try {
      await stopLoop();
      toast.success(t('optimization.stop_loop'));
    } catch {
      toast.error(t('optimization.failed'));
    }
  };

  const handleRetry = () => {
    fetchConfigAndState();
    toast.success(t('common.refresh'));
  };

  // ── Post-optimization action handlers ───────────────────────────────────

  const handleExecuteBest = useCallback(async () => {
    setShowCompletionDialog(false);
    // Find the best experiment from history and re-execute it
    const bestExpId = state?.history.find(
      (h) => h.yield === state.bestYield
    )?.experiment_id;
    if (bestExpId) {
      try {
        await experimentsApi.execute(bestExpId);
        toast.success(t('optimization.completion.executingBest'));
      } catch {
        toast.error(t('optimization.completion.executeFailed'));
      }
    } else {
      toast.error(t('optimization.completion.noBestFound'));
    }
  }, [state, t]);

  const handleNewOptimization = useCallback(async () => {
    setShowCompletionDialog(false);
    try {
      await resetLoop();
      toast.success(t('optimization.completion.resetDone'));
    } catch {
      toast.error(t('optimization.failed'));
    }
  }, [resetLoop, t]);

  const handleExportResults = useCallback(() => {
    setShowCompletionDialog(false);
    // Export optimization history as JSON
    const exportData = {
      goal: config?.goal,
      best_yield: state?.bestYield,
      best_params: state?.bestParams,
      total_iterations: state?.currentIteration,
      history: state?.history,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `optimization_results_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(t('optimization.completion.exported'));
  }, [config, state, t]);

  const handleDismissDialog = useCallback(() => {
    setShowCompletionDialog(false);
  }, []);

  if (isLoading && !config) {
    return (
      <div className="flex h-full items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!config || !state) {
    return (
      <div className="p-6 text-center text-slate-500">
        <p>{t('optimization.failed')}</p>
        <button 
          onClick={handleRetry} 
          className="mt-4 inline-flex items-center gap-1.5 px-3 py-2 text-blue-600 hover:text-blue-700 font-medium"
        >
          <RefreshCw className="h-4 w-4" />
          {t('common.retry')}
        </button>
      </div>
    );
  }

  const isRunning = state.status === "running";
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{t('optimization.title')}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {t('optimization.subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 border border-slate-200 shadow-sm text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${isRunning ? "bg-blue-500 animate-pulse" : "bg-slate-300"}`} />
            <span className="font-medium capitalize text-slate-700">{state.status}</span>
          </div>
          {isRunning ? (
            <button 
              onClick={handleStopLoop} 
              className="flex items-center gap-2 rounded-lg bg-red-50 text-red-700 px-4 py-2 border border-red-200 hover:bg-red-100 transition shadow-sm font-medium"
            >
              <Square className="h-4 w-4" /> {t('optimization.stop_loop')}
            </button>
          ) : (
            <button 
              onClick={handleStartLoop} 
              className="flex items-center gap-2 rounded-lg bg-blue-600 text-white px-4 py-2 border border-blue-700 hover:bg-blue-700 transition shadow-sm font-medium"
            >
              <Play className="h-4 w-4" /> {t('optimization.start_loop')}
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        
        {/* Left Column: Config */}
        <div className="xl:col-span-1 space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-3 mb-4">
              <SettingsIcon className="h-5 w-5 text-slate-400" />
              <h3 className="font-semibold text-slate-900">{t('optimization.configuration')}</h3>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-500">{t('optimization.target_func')}</label>
                <div className="mt-1 flex justify-between items-center bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg text-sm">
                  <span className="font-mono text-slate-700">{config.targetFunction}</span>
                  <Target className="h-4 w-4 text-blue-500" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">{t('optimization.max_iter')}</label>
                <div className="mt-1 text-sm font-medium text-slate-900">{config.maxIterations} {t('optimization.cycles')}</div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">{t('optimization.constraints')}</label>
                <ul className="mt-1 space-y-1">
                  {config.constraints.map((c, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-orange-700 bg-orange-50 px-2 py-1 rounded">
                      <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-slate-900 mb-4">{t('optimization.parameterSpace')}</h3>
            <div className="space-y-3">
              {Object.entries(config.parameterSpace).map(([key, boundary]) => (
                <div key={key} className="p-3 rounded-lg border border-slate-100 bg-slate-50">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-slate-700">{key}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{(boundary as any).type}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                    <span>{(boundary as any).min}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-slate-200" />
                    <span>{(boundary as any).max}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Middle Column: Chart & Current Stats */}
        <div className="xl:col-span-2 flex flex-col gap-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm flex-1">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-semibold text-slate-900">{t('optimization.convergenceCurve')}</h3>
              <div className="text-sm font-medium text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full">
                {t('optimization.iteration', { current: state.currentIteration, max: state.maxIterations })}
              </div>
            </div>
            
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={state.history} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis 
                    dataKey="iteration" 
                    tick={{ fontSize: 12, fill: '#94a3b8' }} 
                    axisLine={{ stroke: '#e2e8f0' }}
                    tickLine={false} 
                  />
                  <YAxis 
                    tick={{ fontSize: 12, fill: '#94a3b8' }} 
                    axisLine={false} 
                    tickLine={false} 
                    domain={['auto', 'auto']}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    labelStyle={{ color: '#64748b', fontWeight: 600, fontSize: '12px' }}
                  />
                  <ReferenceLine y={state.bestYield} stroke="#10b981" strokeDasharray="3 3" />
                  <Line 
                    type="monotone" 
                    dataKey="yield" 
                    stroke="#3b82f6" 
                    strokeWidth={3}
                    dot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
                    activeDot={{ r: 6, fill: '#3b82f6' }} 
                    animationDuration={1500}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            
            <div className="mt-4 pt-4 border-t border-slate-100">
               <div className="flex items-center gap-2 mb-2 text-sm font-medium text-slate-700">
                 <FlaskConical className="h-4 w-4 text-purple-500" />
                 {t('optimization.current_iter_details')}
               </div>
               <div className="grid grid-cols-3 gap-4">
                 {Object.entries(state.history[state.history.length-1]?.params || {}).map(([k, v]) => (
                   <div key={k} className="bg-slate-50 rounded-lg p-2 text-center border border-slate-100">
                     <div className="text-[10px] text-slate-500 mb-1">{k}</div>
                     <div className="text-sm font-mono font-medium">{String(v)}</div>
                   </div>
                 ))}
               </div>
            </div>
          </div>
        </div>

        {/* Right Column: Best Results & Agent Next Suggestion */}
        <div className="xl:col-span-1 space-y-6">
          <div className="rounded-2xl border border-green-200 bg-green-50/50 p-5 shadow-sm">
            <div className="flex items-center gap-2 pb-3 mb-4 border-b border-green-100">
              <Trophy className="h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-green-900">{t('optimization.globalBest')}</h3>
            </div>
            <div className="text-center mb-6">
              <div className="text-sm font-medium text-green-700">{t('optimization.highestYieldAchieved')}</div>
              <div className="text-3xl font-bold text-green-600 mt-1">{state.bestYield.toFixed(2)}%</div>
            </div>
            <div className="space-y-2">
              <div className="text-xs font-semibold text-green-800 uppercase tracking-wider mb-2">{t('optimization.optimalParameters')}</div>
              {Object.entries(state.bestParams).map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm py-1.5 border-b border-green-100 last:border-0">
                  <span className="text-green-700">{k}</span>
                  <span className="font-mono font-medium text-green-900">{String(v)}</span>
                </div>
              ))}
            </div>
          </div>

          {state.nextSuggestion && (
            <div className="rounded-2xl border border-purple-200 bg-purple-50/50 p-5 shadow-sm">
              <div className="flex items-center gap-2 pb-3 mb-4 border-b border-purple-100">
                <BrainCircuit className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-purple-900">{t('optimization.agentProposal')}</h3>
              </div>
              <p className="text-sm text-purple-800 mb-4 leading-relaxed bg-white/60 p-3 rounded-lg border border-purple-100">
                {state.nextSuggestion.reason}
              </p>
              
              <div className="mb-4">
                <div className="text-xs font-medium text-purple-600 mb-1 flex justify-between">
                  <span>{t('optimization.predictedYield')}</span>
                  <span className="font-bold">{state.nextSuggestion.predictedYield.toFixed(1)}%</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-xs font-semibold text-purple-800 uppercase tracking-wider mb-2">{t('optimization.suggestedParams')}</div>
                {Object.entries(state.nextSuggestion.suggestedParams).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm py-1.5 border-b border-purple-100 last:border-0">
                    <span className="text-purple-700">{k}</span>
                    <span className="font-mono font-medium text-purple-900">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Optimization Completion Dialog ────────────────────────────────── */}
      {showCompletionDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="relative w-full max-w-lg mx-4 rounded-2xl border border-slate-200 bg-white shadow-2xl">
            {/* Close button */}
            <button
              onClick={handleDismissDialog}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Header */}
            <div className="px-6 pt-6 pb-4 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-full ${
                  state?.status === "completed" ? "bg-green-100" : state?.status === "error" ? "bg-red-100" : "bg-amber-100"
                }`}>
                  {state?.status === "completed" ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : state?.status === "error" ? (
                    <AlertCircle className="h-5 w-5 text-red-600" />
                  ) : (
                    <Square className="h-5 w-5 text-amber-600" />
                  )}
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">
                    {t(`optimization.completion.title_${state?.status === "completed" ? "completed" : state?.status === "error" ? "error" : "stopped"}`)}
                  </h3>
                  <p className="text-sm text-slate-500">
                    {t('optimization.completion.summary', {
                      iterations: state?.currentIteration ?? 0,
                      best: state?.bestYield?.toFixed(2) ?? "N/A",
                    })}
                  </p>
                </div>
              </div>
            </div>

            {/* Best result summary */}
            {state && state.bestYield > 0 && (
              <div className="px-6 py-4 bg-green-50/50 border-b border-slate-100">
                <div className="flex items-center gap-2 mb-2">
                  <Trophy className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-semibold text-green-800">{t('optimization.globalBest')}</span>
                  <span className="ml-auto text-lg font-bold text-green-600">{state.bestYield.toFixed(2)}%</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(state.bestParams).map(([k, v]) => (
                    <span key={k} className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                      {k}: {String(v)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="px-6 py-5 space-y-3">
              <p className="text-sm font-medium text-slate-700 mb-3">{t('optimization.completion.whatNext')}</p>

              <button
                onClick={handleExecuteBest}
                className="w-full flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left hover:bg-blue-100 transition group"
              >
                <Beaker className="h-5 w-5 text-blue-600 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-blue-900">{t('optimization.completion.executeBest')}</div>
                  <div className="text-xs text-blue-600">{t('optimization.completion.executeBestDesc')}</div>
                </div>
              </button>

              <button
                onClick={handleNewOptimization}
                className="w-full flex items-center gap-3 rounded-xl border border-purple-200 bg-purple-50 px-4 py-3 text-left hover:bg-purple-100 transition group"
              >
                <RotateCcw className="h-5 w-5 text-purple-600 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-purple-900">{t('optimization.completion.newOptimization')}</div>
                  <div className="text-xs text-purple-600">{t('optimization.completion.newOptimizationDesc')}</div>
                </div>
              </button>

              <button
                onClick={handleExportResults}
                className="w-full flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left hover:bg-slate-100 transition group"
              >
                <Download className="h-5 w-5 text-slate-600 shrink-0" />
                <div>
                  <div className="text-sm font-semibold text-slate-900">{t('optimization.completion.exportResults')}</div>
                  <div className="text-xs text-slate-500">{t('optimization.completion.exportResultsDesc')}</div>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
