import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Activity,
  BarChart,
  BookOpen,
  Bot,
  Clock,
  Database,
  FileText,
  FlaskConical,
  FolderOpen,
  Lightbulb,
  MessageSquare,
  Microscope,
  PlayCircle,
  Plus,
  Server,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ExperimentCreateDialog } from '@/components/ExperimentCreateDialog';
import ExperimentSelector from '@/components/ExperimentSelector';
import ChatWindow from '@/components/ChatWindow';

interface SystemStatus {
  autohyseeker: boolean;
  microhyseeker: boolean;
  database: boolean;
  agents: { running: number; total: number };
}

interface Statistics {
  totalExperiments: number;
  todayExperiments: number;
  successRate: number;
  successTrend: 'up' | 'down' | 'stable';
  avgDuration: string;
}

interface ActivityLog {
  id: string;
  timestamp: string;
  type: 'experiment' | 'agent' | 'system' | 'template';
  description: string;
}

interface SystemHealth {
  cpu: number[];
  memory: number[];
  apiResponseTime: number[];
  timestamps: string[];
}

interface ExperimentRecord {
  exp_id: string;
  name: string;
  description: string;
  status: 'created' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  tags?: string[];
  steps?: Array<{ step_type: string; description?: string; params?: Record<string, unknown> }>;
}

function formatTime(value?: string) {
  if (!value) return '--';
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function inferSource(exp: ExperimentRecord) {
  const sourceTag = exp.tags?.find((tag) => tag.startsWith('operator:'));
  if (sourceTag) return sourceTag.replace('operator:', '');
  return exp.description?.includes('模板') ? 'template' : 'manual';
}

function summarizeCurrentStep(exp: ExperimentRecord) {
  const current = exp.steps?.[0];
  if (!current) return null;
  const typeLabel: Record<string, string> = { prep_sol: '配液', transfer: '移液', flush: '冲洗', echem: '电化学', blank: '空白', evacuate: '排空' };
  return `${typeLabel[current.step_type] ?? current.step_type}${current.description ? ` · ${current.description}` : ''}`;
}

export function Overview() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    autohyseeker: false,
    microhyseeker: false,
    database: false,
    agents: { running: 0, total: 5 },
  });
  const [statistics, setStatistics] = useState<Statistics>({
    totalExperiments: 0,
    todayExperiments: 0,
    successRate: 0,
    successTrend: 'stable',
    avgDuration: '0m',
  });
  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    cpu: [],
    memory: [],
    apiResponseTime: [],
    timestamps: [],
  });
  const [recentExperiments, setRecentExperiments] = useState<ExperimentRecord[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showExperimentSelector, setShowExperimentSelector] = useState(false);
  const [showKnowledgeChat, setShowKnowledgeChat] = useState(false);

  useEffect(() => {
    fetchOverviewData();
    const interval = setInterval(fetchActivities, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchOverviewData = async () => {
    try {
      const [statusRes, statsRes, activitiesRes, healthRes, recentRes] = await Promise.all([
        fetch('/api/system/status').catch(() => null),
        fetch('/api/experiments/statistics').catch(() => null),
        fetch('/api/system/activities?limit=10').catch(() => null),
        fetch('/api/system/health').catch(() => null),
        fetch('/api/experiments/recent?limit=8').catch(() => null),
      ]);

      if (statusRes?.ok) setSystemStatus(await statusRes.json());
      if (statsRes?.ok) setStatistics(await statsRes.json());
      if (activitiesRes?.ok) setActivities(await activitiesRes.json());
      if (healthRes?.ok) setSystemHealth(await healthRes.json());
      if (recentRes?.ok) {
        const data = await recentRes.json();
        setRecentExperiments(data.experiments ?? []);
      }
    } catch (error) {
      console.error('Failed to fetch overview data:', error);
    }
  };

  const fetchActivities = async () => {
    try {
      const res = await fetch('/api/system/activities?limit=10');
      if (res.ok) setActivities(await res.json());
    } catch (error) {
      console.error('Failed to fetch activities:', error);
    }
  };

  const handleAnalyzeRecent = async () => {
    try {
      await fetch('/api/experiments/analyze-recent', { method: 'POST' });
      alert(t('overview.analyzeSuccess'));
    } catch {
      alert(t('overview.analyzeError'));
    }
  };

  const handleGetSuggestions = async () => {
    try {
      const res = await fetch('/api/experiments/suggestions');
      const data = await res.json();
      alert(JSON.stringify(data, null, 2));
    } catch {
      alert(t('overview.suggestionsError'));
    }
  };

  const handleLoadExperiment = (experiment: { exp_id: string }) => {
    navigate(`/experiments/${experiment.exp_id}`);
  };

  // Simple per-element fade-in
  
  const getActivityColor = (type: string) => {
    switch (type) {
      case 'experiment':
        return 'text-blue-600 bg-blue-50';
      case 'agent':
        return 'text-green-600 bg-green-50';
      case 'system':
        return 'text-yellow-600 bg-yellow-50';
      case 'template':
        return 'text-purple-600 bg-purple-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const runningExperiments = useMemo(
    () => recentExperiments.filter((item) => item.status === 'running').slice(0, 3),
    [recentExperiments],
  );

  return (
    <div className="space-y-6 p-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-800 p-6 text-white shadow-sm"
      >
        <div className="grid gap-6 lg:grid-cols-[1.5fr,1fr] lg:items-center">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-100">AI Experiment Steward</p>
            <h1 className="mt-3 text-3xl font-bold">{t('overview.heroTitle')}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-blue-50/90">
              {t('overview.heroSubtitle')}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() => setShowCreateDialog(true)}
                className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-100"
              >
                {t('overview.startNewExperiment')}
              </button>
              <button
                onClick={() => setShowKnowledgeChat(true)}
                className="rounded-lg border border-white/30 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
              >
                {t('overview.openKnowledgeChat')}
              </button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            {[
              {
                icon: FlaskConical,
                title: t('overview.beforeExperiment'),
                desc: t('overview.beforeExperimentDesc'),
              },
              {
                icon: Microscope,
                title: t('overview.duringExperiment'),
                desc: t('overview.duringExperimentDesc'),
              },
              {
                icon: Sparkles,
                title: t('overview.afterExperiment'),
                desc: t('overview.afterExperimentDesc'),
              },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="rounded-xl border border-white/15 bg-white/10 p-4 backdrop-blur-sm">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Icon className="h-4 w-4" />
                    {item.title}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-blue-50/85">{item.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {[
          {
            title: t('overview.step1Title'),
            desc: t('overview.step1Desc'),
            action: t('overview.step1Action'),
            onClick: () => setShowCreateDialog(true),
          },
          {
            title: t('overview.step2Title'),
            desc: t('overview.step2Desc'),
            action: t('overview.step2Action'),
            onClick: () => navigate('/dashboard'),
          },
          {
            title: t('overview.step3Title'),
            desc: t('overview.step3Desc'),
            action: t('overview.step3Action'),
            onClick: () => setShowKnowledgeChat(true),
          },
        ].map((card) => (
          <div key={card.title} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">{card.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{card.desc}</p>
            <button
              onClick={card.onClick}
              className="mt-4 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              {card.action}
            </button>
          </div>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{t('overview.runningExperiments')}</h2>
              <p className="mt-1 text-sm text-slate-600">{t('overview.runningExperimentsDesc')}</p>
            </div>
            <button onClick={() => navigate('/dashboard')} className="text-sm font-medium text-blue-600 hover:text-blue-700">
              {t('overview.openLiveMonitor')}
            </button>
          </div>

          <div className="mt-4 grid gap-4">
            {runningExperiments.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-5 py-8 text-sm text-slate-500">
                {t('overview.noRunningExperiments')}
              </div>
            ) : (
              runningExperiments.map((exp) => (
                <button
                  key={exp.exp_id}
                  type="button"
                  onClick={() => handleLoadExperiment(exp)}
                  className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-left transition hover:border-blue-300 hover:bg-blue-50/40"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <PlayCircle className="h-5 w-5 text-blue-600" />
                        <h3 className="text-base font-semibold text-slate-900">{exp.name}</h3>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{exp.description || t('overview.noExtraDesc')}</p>
                    </div>
                    <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">{exp.status}</span>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <div className="rounded-xl bg-white px-4 py-3">
                      <p className="text-xs text-slate-500">{t('overview.currentStep')}</p>
                      <p className="mt-1 text-sm font-medium text-slate-900">{summarizeCurrentStep(exp) || t('overview.noStepInfo')}</p>
                    </div>
                    <div className="rounded-xl bg-white px-4 py-3">
                      <p className="text-xs text-slate-500">{t('overview.statusLabel')}</p>
                      <p className="mt-1 text-sm font-medium text-slate-900">{t('overview.running')}</p>
                    </div>
                    <div className="rounded-xl bg-white px-4 py-3">
                      <p className="text-xs text-slate-500">{t('overview.startTime')}</p>
                      <p className="mt-1 text-sm font-medium text-slate-900">{formatTime(exp.started_at || exp.created_at)}</p>
                    </div>
                    <div className="rounded-xl bg-white px-4 py-3">
                      <p className="text-xs text-slate-500">{t('overview.source')}</p>
                      <p className="mt-1 text-sm font-medium text-slate-900">{inferSource(exp)}</p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">{t('overview.knowledgeManagement')}</h2>
              <p className="mt-1 text-sm text-slate-600">{t('overview.knowledgeChatDesc')}</p>
            </div>
            <button onClick={() => setShowKnowledgeChat(true)} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800">
              {t('overview.openChat')}
            </button>
          </div>

          <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-900">
              <BookOpen className="h-4 w-4" />
              {t('overview.currentContext')}
            </div>
            <ul className="mt-3 space-y-2 text-sm text-blue-900">
              <li>• {t('overview.recentExpCount')}：{recentExperiments.length}</li>
              <li>• {t('overview.runningExpCount')}：{runningExperiments.length}</li>
              <li>• {t('overview.canAskAbout')}</li>
            </ul>
          </div>

          <div className="mt-4 space-y-3">
            {[
              '电化学步骤应该先做 CV 还是 EIS？依据是什么？',
              '根据近期实验数据，下一轮应优先调整哪个步骤？',
              '移液步骤执行异常的常见原因有哪些？',
            ].map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setShowKnowledgeChat(true)}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-700 transition hover:border-blue-300 hover:bg-slate-50"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.autohyseeker')}</p>
              <div className="mt-2 flex items-center">
                <div className={`h-3 w-3 rounded-full ${systemStatus.autohyseeker ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="ml-2 text-sm font-medium">{systemStatus.autohyseeker ? t('overview.online') : t('overview.offline')}</span>
              </div>
            </div>
            <Server className="h-8 w-8 text-blue-500" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.microhyseeker')}</p>
              <div className="mt-2 flex items-center">
                <div className={`h-3 w-3 rounded-full ${systemStatus.microhyseeker ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="ml-2 text-sm font-medium">{systemStatus.microhyseeker ? t('overview.connected') : t('overview.disconnected')}</span>
              </div>
            </div>
            <Activity className="h-8 w-8 text-green-500" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.database')}</p>
              <div className="mt-2 flex items-center">
                <div className={`h-3 w-3 rounded-full ${systemStatus.database ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="ml-2 text-sm font-medium">{systemStatus.database ? t('overview.online') : t('overview.offline')}</span>
              </div>
            </div>
            <Database className="h-8 w-8 text-purple-500" />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.agents')}</p>
              <p className="mt-2 text-2xl font-bold">{systemStatus.agents.running}/{systemStatus.agents.total}</p>
              <p className="text-xs text-gray-500">{t('overview.running')}</p>
            </div>
            <Bot className="h-8 w-8 text-orange-500" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 p-6 text-white shadow-sm transition-all duration-200 hover:shadow-md">
          <p className="text-sm opacity-90">{t('overview.totalExperiments')}</p>
          <p className="mt-2 text-3xl font-bold">{statistics.totalExperiments}</p>
        </div>

        <div className="rounded-xl bg-gradient-to-br from-green-500 to-green-600 p-6 text-white shadow-sm transition-all duration-200 hover:shadow-md">
          <p className="text-sm opacity-90">{t('overview.todayExperiments')}</p>
          <p className="mt-2 text-3xl font-bold">{statistics.todayExperiments}</p>
        </div>

        <div className="rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 p-6 text-white shadow-sm transition-all duration-200 hover:shadow-md">
          <p className="text-sm opacity-90">{t('overview.successRate')}</p>
          <div className="mt-2 flex items-center">
            <p className="text-3xl font-bold">{statistics.successRate}%</p>
            {statistics.successTrend === 'up' && <TrendingUp className="ml-2 h-6 w-6" />}
            {statistics.successTrend === 'down' && <TrendingDown className="ml-2 h-6 w-6" />}
          </div>
        </div>

        <div className="rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 p-6 text-white shadow-sm transition-all duration-200 hover:shadow-md">
          <p className="text-sm opacity-90">{t('overview.avgDuration')}</p>
          <p className="mt-2 text-3xl font-bold">{statistics.avgDuration || '--'}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
          <h2 className="mb-4 flex items-center text-lg font-semibold">
            <Clock className="mr-2 h-5 w-5 text-blue-500" />
            {t('overview.recentActivities')}
          </h2>
          <div className="max-h-96 space-y-3 overflow-y-auto">
            {activities.length === 0 ? (
              <p className="py-8 text-center text-gray-500">{t('overview.noActivities')}</p>
            ) : (
              activities.map((activity) => (
                <div key={activity.id} className="flex items-start space-x-3 rounded-lg p-3 transition-colors hover:bg-gray-50">
                  <div className={`rounded-lg p-2 ${getActivityColor(activity.type)}`}>
                    {activity.type === 'experiment' && <Activity className="h-4 w-4" />}
                    {activity.type === 'agent' && <Server className="h-4 w-4" />}
                    {activity.type === 'system' && <Database className="h-4 w-4" />}
                    {activity.type === 'template' && <FileText className="h-4 w-4" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{activity.description}</p>
                    <p className="text-xs text-gray-500">{activity.timestamp}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
          <h2 className="mb-4 text-lg font-semibold">{t('overview.quickEntry')}</h2>
          <div className="grid grid-cols-2 gap-4">
            <button onClick={() => setShowCreateDialog(true)} className="flex flex-col items-center justify-center rounded-xl bg-blue-50 p-6 transition-all hover:bg-blue-100 active:scale-[0.98]">
              <Plus className="mb-2 h-8 w-8 text-blue-600" />
              <span className="text-sm font-medium text-blue-600">{t('overview.stepEditor')}</span>
            </button>

            <button onClick={() => setShowKnowledgeChat(true)} className="flex flex-col items-center justify-center rounded-xl bg-cyan-50 p-6 transition-all hover:bg-cyan-100 active:scale-[0.98]">
              <MessageSquare className="mb-2 h-8 w-8 text-cyan-600" />
              <span className="text-sm font-medium text-cyan-600">{t('overview.knowledgeChat')}</span>
            </button>

            <button onClick={handleAnalyzeRecent} className="flex flex-col items-center justify-center rounded-xl bg-purple-50 p-6 transition-all hover:bg-purple-100 active:scale-[0.98]">
              <BarChart className="mb-2 h-8 w-8 text-purple-600" />
              <span className="text-sm font-medium text-purple-600">{t('overview.dataAnalysisAssistant')}</span>
            </button>

            <button onClick={handleGetSuggestions} className="flex flex-col items-center justify-center rounded-xl bg-orange-50 p-6 transition-all hover:bg-orange-100 active:scale-[0.98]">
              <Lightbulb className="mb-2 h-8 w-8 text-orange-600" />
              <span className="text-sm font-medium text-orange-600">{t('overview.schemeDesignAssistant')}</span>
            </button>

            <button onClick={() => navigate('/dashboard')} className="col-span-2 flex flex-col items-center justify-center rounded-xl bg-green-50 p-6 transition-all hover:bg-green-100 active:scale-[0.98]">
              <Microscope className="mb-2 h-8 w-8 text-green-600" />
              <span className="text-sm font-medium text-green-600">{t('overview.monitorAssistant')}</span>
            </button>

            <button onClick={() => setShowExperimentSelector(true)} className="col-span-2 flex flex-col items-center justify-center rounded-xl bg-slate-100 p-6 transition-all hover:bg-slate-200 active:scale-[0.98]">
              <FolderOpen className="mb-2 h-8 w-8 text-slate-700" />
              <span className="text-sm font-medium text-slate-700">{t('overview.loadRecentExperiments')}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-200 hover:shadow-md">
        <h2 className="mb-4 flex items-center text-lg font-semibold">
          <BarChart className="mr-2 h-5 w-5 text-blue-500" />
          {t('overview.systemHealth')}
        </h2>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div>
            <p className="mb-2 text-sm text-gray-600">{t('overview.cpuUsage')}</p>
            <div className="flex h-32 items-end space-x-1">
              {systemHealth.cpu.length > 0 ? (
                systemHealth.cpu.map((value, index) => (
                  <div key={index} className="flex-1 rounded-t bg-blue-500" style={{ height: `${value}%` }} />
                ))
              ) : (
                <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">{t('overview.noData')}</div>
              )}
            </div>
          </div>
          <div>
            <p className="mb-2 text-sm text-gray-600">{t('overview.memoryUsage')}</p>
            <div className="flex h-32 items-end space-x-1">
              {systemHealth.memory.length > 0 ? (
                systemHealth.memory.map((value, index) => (
                  <div key={index} className="flex-1 rounded-t bg-green-500" style={{ height: `${value}%` }} />
                ))
              ) : (
                <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">{t('overview.noData')}</div>
              )}
            </div>
          </div>
          <div>
            <p className="mb-2 text-sm text-gray-600">{t('overview.apiResponseTime')}</p>
            <div className="flex h-32 items-end space-x-1">
              {systemHealth.apiResponseTime.length > 0 ? (
                systemHealth.apiResponseTime.map((value, index) => (
                  <div key={index} className="flex-1 rounded-t bg-purple-500" style={{ height: `${Math.min(value / 10, 100)}%` }} />
                ))
              ) : (
                <div className="flex h-full w-full items-center justify-center text-sm text-gray-400">{t('overview.noData')}</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showCreateDialog && (
        <ExperimentCreateDialog
          onClose={() => setShowCreateDialog(false)}
          onSubmit={(experiment) => {
            navigate(`/experiments/${(experiment as Record<string, string>).exp_id}`);
          }}
        />
      )}

      {showExperimentSelector && (
        <ExperimentSelector isOpen={showExperimentSelector} onClose={() => setShowExperimentSelector(false)} onSelect={handleLoadExperiment} />
      )}

      <ChatWindow isOpen={showKnowledgeChat} onClose={() => setShowKnowledgeChat(false)} />
    </div>
  );
}
