import { useTranslation } from "react-i18next";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { monitorApi, MonitorStatus } from "@/api/monitor";
import { Activity, AlertTriangle, CheckCircle2, Server, Power, Watch, RotateCw } from "lucide-react";
import { SkeletonList } from "@/components/Skeleton";
import toast from "react-hot-toast";
import { useEffect, useRef } from "react";

const AlertDetailCard = ({ alert }: { alert: Record<string, any> }) => {
  const entries = Object.entries(alert).map(([key, value]) => ({
    label: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    value: value === null || value === undefined ? '—' : 
           typeof value === 'boolean' ? (value ? '是' : '否') :
           typeof value === 'object' ? JSON.stringify(value) : 
           String(value)
  }));

  return (
    <div className="space-y-1.5 text-xs">
      {entries.map(({ label, value }) => (
        <div key={label} className="flex items-start gap-2">
          <span className="w-20 font-medium text-slate-600 flex-shrink-0">{label}:</span>
          <span className="text-slate-700 break-all flex-1">{value}</span>
        </div>
      ))}
    </div>
  );
};

export function Diagnostics() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const lastErrorRef = useRef<string | null>(null);

  const { data: status, isLoading, error, refetch } = useQuery<MonitorStatus>({
    queryKey: ['monitor-status'],
    queryFn: () => monitorApi.getStatus(),
    refetchInterval: 3000,
    retry: 2,
  });

  const handleToggle = async () => {
    if (!status) return;
    try {
      await monitorApi.toggleHeartbeat(!status.heartbeat_enabled);
      await queryClient.invalidateQueries({ queryKey: ['monitor-status'] });
      toast.success(status.heartbeat_enabled ? t('diagnostics.heartbeatDisabled') : t('diagnostics.heartbeatEnabled'));
    } catch (err: any) {
      toast.error(err.message || t('diagnostics.heartbeatToggleFailed'));
    }
  };

  const handleRetry = () => {
    refetch();
    toast.success(t('diagnostics.retrying'));
  };

  // Show error toast once when error occurs
  useEffect(() => {
    if (!error || isLoading) return;

    const message = (error as any).message || t('diagnostics.errorStart');
    if (lastErrorRef.current !== message) {
      toast.error(message);
      lastErrorRef.current = message;
    }
  }, [error, isLoading, t]);

  return (
    <div className="flex h-full flex-col bg-slate-50/50">
      <div className="flex flex-wrap items-start justify-between gap-4 p-4 md:p-6 lg:p-8 pb-0">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">{t('nav.diagnostics')}</h2>
          <p className="mt-1 text-sm text-slate-500">{t('diagnostics.subtitle')}</p>
        </div>
        {status && (
          <button 
            onClick={handleRetry}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm text-slate-700 hover:bg-slate-50 transition"
          >
            <RotateCw className="h-4 w-4" />
            {t('common.refresh')}
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
        {isLoading && !status ? (
          <div className="space-y-6">
            <SkeletonList count={2} />
          </div>
        ) : error && !status ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-red-800">{t('diagnostics.errorStart')}</p>
                <p className="text-sm text-red-700 mt-1">{(error as any).message}</p>
                <button 
                  onClick={handleRetry}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700 transition"
                >
                  <RotateCw className="h-4 w-4" />
                  {t('common.retry')}
                </button>
              </div>
            </div>
          </div>
        ) : status ? (
          <div className="grid gap-6 md:grid-cols-2">
            {/* L1 Status Card */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl ${status.l1_status === 'ok' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                  <Server className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-slate-800 text-lg flex items-center gap-2">
                    {t('diagnostics.l1Title')}
                    {status.l1_status === 'ok' ? (
                      <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 ring-1 ring-inset ring-emerald-600/20">{t('diagnostics.statusActive')}</span>
                    ) : (
                      <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20">{t('diagnostics.statusAlert')}</span>
                    )}
                  </h3>
                  <p className="text-sm text-slate-500 mt-1">{t('diagnostics.l1Desc')}</p>
                </div>
              </div>
              <div className="mt-6 border-t border-slate-100 pt-4">
                {status.l1_alerts && status.l1_alerts.length > 0 ? (
                  <div className="space-y-3">
                    {status.l1_alerts.map((alert, idx) => (
                      <div key={idx} className="bg-red-50/50 border border-red-100 p-3 rounded-lg">
                        <div className="flex items-start gap-2 mb-2">
                          <AlertTriangle className="h-4 w-4 shrink-0 flex-none text-red-600 mt-0.5" />
                          <span className="text-sm font-medium text-red-700">Alert #{idx + 1}</span>
                        </div>
                        <AlertDetailCard alert={alert} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    {t('diagnostics.l1NoAlerts')}
                  </div>
                )}
              </div>
            </div>

            {/* L2 Status Card */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl ${status.heartbeat_enabled ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
                  <Activity className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-slate-800 text-lg flex items-center gap-2">
                      {t('diagnostics.l2Title')}
                      {status.heartbeat_enabled ? (
                        <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20">{t('diagnostics.statusAnalyzing')}</span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-500/20">{t('diagnostics.statusDisabled')}</span>
                      )}
                    </h3>
                    <button 
                      onClick={handleToggle}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${status.heartbeat_enabled ? 'bg-blue-600' : 'bg-slate-200'}`}
                    >
                      <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${status.heartbeat_enabled ? 'translate-x-5' : 'translate-x-0'}`} />
                    </button>
                  </div>
                  <p className="text-sm text-slate-500 mt-1">{t('diagnostics.l2Desc')}</p>
                </div>
              </div>
              
              <div className="mt-6 border-t border-slate-100 pt-4">
                <div className="flex items-center gap-4 text-sm text-slate-600 mb-4">
                  <div className="flex items-center gap-1.5">
                    <Watch className="h-4 w-4" />
                    <span>{t('diagnostics.lastHeartbeat')}: {status.last_heartbeat ? new Date(status.last_heartbeat).toLocaleTimeString('zh-CN') : 'N/A'}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Power className="h-4 w-4" />
                    <span>{t('diagnostics.status')}: <span className="font-medium text-slate-800">{status.l2_status}</span></span>
                  </div>
                </div>

                {status.l2_diagnostics ? (
                  <div className="text-sm bg-slate-50 p-4 rounded-lg border border-slate-100 whitespace-pre-wrap font-mono text-slate-700 max-h-48 overflow-y-auto">
                    {status.l2_diagnostics}
                  </div>
                ) : (
                  <div className="text-sm text-slate-400 italic">
                    {t('diagnostics.noReports')}
                  </div>
                )}
              </div>
            </div>

            {/* Experiment Context Card */}
            <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
              <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                {t('diagnostics.systemStatus')}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                 <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                    <div className="text-xs font-medium text-slate-500 mb-1">{t('diagnostics.activeExpId')}</div>
                    <div className="font-mono text-sm text-slate-900">{status.active_experiment_id || t('diagnostics.none')}</div>
                 </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
