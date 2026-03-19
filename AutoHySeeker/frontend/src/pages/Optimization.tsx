import { useTranslation } from "react-i18next";
import { useEffect } from "react";
import { useOptimizationStore } from "@/stores/optimizationStore";
import { motion } from "framer-motion";
import { Play, Square, Settings as SettingsIcon, BrainCircuit, RefreshCw, Trophy, FlaskConical, Target, AlertCircle } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

export function Optimization() {
  const { t } = useTranslation();
  const { config, state, isLoading, fetchConfigAndState, startLoop, stopLoop } = useOptimizationStore();

  useEffect(() => {
    fetchConfigAndState();
  }, [fetchConfigAndState]);

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
        <p>Failed to load optimization context.</p>
        <button onClick={fetchConfigAndState} className="mt-4 text-blue-500 hover:underline">Retry</button>
      </div>
    );
  }

  const isRunning = state.status === "running";
  const progressPercent = (state.currentIteration / state.maxIterations) * 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{t('optimization.title', 'Optimization Loop')}</h2>
          <p className="mt-1 text-sm text-slate-500">
            Autonomous closed-loop experimentation controlled by Designer Agent.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 border border-slate-200 shadow-sm text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${isRunning ? "bg-blue-500 animate-pulse" : "bg-slate-300"}`} />
            <span className="font-medium capitalize text-slate-700">{state.status}</span>
          </div>
          {isRunning ? (
            <button onClick={stopLoop} className="flex items-center gap-2 rounded-lg bg-red-50 text-red-700 px-4 py-2 border border-red-200 hover:bg-red-100 transition shadow-sm font-medium">
              <Square className="h-4 w-4" /> Stop Loop
            </button>
          ) : (
            <button onClick={startLoop} className="flex items-center gap-2 rounded-lg bg-blue-600 text-white px-4 py-2 border border-blue-700 hover:bg-blue-700 transition shadow-sm font-medium">
              <Play className="h-4 w-4" /> Start Loop
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
              <h3 className="font-semibold text-slate-900">Configuration</h3>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-500">{t('optimization.target_func', 'Target Function')}</label>
                <div className="mt-1 flex justify-between items-center bg-slate-50 border border-slate-200 px-3 py-2 rounded-lg text-sm">
                  <span className="font-mono text-slate-700">{config.targetFunction}</span>
                  <Target className="h-4 w-4 text-blue-500" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">{t('optimization.max_iter', 'Max Iterations')}</label>
                <div className="mt-1 text-sm font-medium text-slate-900">{config.maxIterations} cycles</div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-500">Constraints</label>
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
            <h3 className="font-semibold text-slate-900 mb-4">Parameter Space</h3>
            <div className="space-y-3">
              {Object.entries(config.parameterSpace).map(([key, boundary]) => (
                <div key={key} className="p-3 rounded-lg border border-slate-100 bg-slate-50">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-slate-700">{key}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{boundary.type}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                    <span>{boundary.min}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-slate-200" />
                    <span>{boundary.max}</span>
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
              <h3 className="font-semibold text-slate-900">Convergence Curve</h3>
              <div className="text-sm font-medium text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full">
                Iteration: {state.currentIteration} / {state.maxIterations}
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
                 Current Iteration Details
               </div>
               <div className="grid grid-cols-3 gap-4">
                 {Object.entries(state.history[state.history.length-1]?.params || {}).map(([k, v]) => (
                   <div key={k} className="bg-slate-50 rounded-lg p-2 text-center border border-slate-100">
                     <div className="text-[10px] text-slate-500 mb-1">{k}</div>
                     <div className="text-sm font-mono font-medium">{v}</div>
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
              <h3 className="font-semibold text-green-900">Global Best</h3>
            </div>
            <div className="text-center mb-6">
              <div className="text-sm font-medium text-green-700">Highest Yield Achieved</div>
              <div className="text-3xl font-bold text-green-600 mt-1">{state.bestYield.toFixed(2)}%</div>
            </div>
            <div className="space-y-2">
              <div className="text-xs font-semibold text-green-800 uppercase tracking-wider mb-2">Optimal Parameters</div>
              {Object.entries(state.bestParams).map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm py-1.5 border-b border-green-100 last:border-0">
                  <span className="text-green-700">{k}</span>
                  <span className="font-mono font-medium text-green-900">{v}</span>
                </div>
              ))}
            </div>
          </div>

          {state.nextSuggestion && (
            <div className="rounded-2xl border border-purple-200 bg-purple-50/50 p-5 shadow-sm">
              <div className="flex items-center gap-2 pb-3 mb-4 border-b border-purple-100">
                <BrainCircuit className="h-5 w-5 text-purple-600" />
                <h3 className="font-semibold text-purple-900">Agent Proposal</h3>
              </div>
              <p className="text-sm text-purple-800 mb-4 leading-relaxed bg-white/60 p-3 rounded-lg border border-purple-100">
                {state.nextSuggestion.reason}
              </p>
              
              <div className="mb-4">
                <div className="text-xs font-medium text-purple-600 mb-1 flex justify-between">
                  <span>Predicted Yield</span>
                  <span className="font-bold">{state.nextSuggestion.predictedYield.toFixed(1)}%</span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-xs font-semibold text-purple-800 uppercase tracking-wider mb-2">Suggested Params</div>
                {Object.entries(state.nextSuggestion.suggestedParams).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm py-1.5 border-b border-purple-100 last:border-0">
                    <span className="text-purple-700">{k}</span>
                    <span className="font-mono font-medium text-purple-900">{v}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
