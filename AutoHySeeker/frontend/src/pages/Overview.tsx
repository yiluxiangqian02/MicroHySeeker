import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import {
  Server,
  Database,
  Activity,
  TrendingUp,
  TrendingDown,
  Plus,
  FileText,
  BarChart,
  Lightbulb,
  Clock,
  FolderOpen,
  FlaskConical,
  Microscope,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ExperimentCreateDialog } from '@/components/ExperimentCreateDialog';
import ExperimentSelector from '@/components/ExperimentSelector';

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

export function Overview() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    autohyseeker: true,
    microhyseeker: true,
    database: true,
    agents: { running: 3, total: 5 },
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
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showExperimentSelector, setShowExperimentSelector] = useState(false);

  useEffect(() => {
    fetchOverviewData();
    const interval = setInterval(fetchActivities, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchOverviewData = async () => {
    try {
      const [statusRes, statsRes, activitiesRes, healthRes] = await Promise.all([
        fetch('/api/system/status').catch(() => null),
        fetch('/api/experiments/statistics').catch(() => null),
        fetch('/api/system/activities?limit=10').catch(() => null),
        fetch('/api/system/health').catch(() => null),
      ]);

      if (statusRes?.ok) setSystemStatus(await statusRes.json());
      if (statsRes?.ok) setStatistics(await statsRes.json());
      if (activitiesRes?.ok) setActivities(await activitiesRes.json());
      if (healthRes?.ok) setSystemHealth(await healthRes.json());
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
    } catch (error) {
      alert(t('overview.analyzeError'));
    }
  };

  const handleGetSuggestions = async () => {
    try {
      const res = await fetch('/api/experiments/suggestions');
      const data = await res.json();
      alert(JSON.stringify(data, null, 2));
    } catch (error) {
      alert(t('overview.suggestionsError'));
    }
  };

  const handleLoadExperiment = (experiment: any) => {
    // Navigate to experiment detail or load into create dialog
    navigate(`/experiments/${experiment.exp_id}`);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

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

  return (
    <motion.div
      className="p-6 space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.section
        variants={itemVariants}
        className="overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-800 p-6 text-white shadow-sm"
      >
        <div className="grid gap-6 lg:grid-cols-[1.5fr,1fr] lg:items-center">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-100">AI Experiment Steward</p>
            <h1 className="mt-3 text-3xl font-bold">像科研助理一样组织实验，而不是像后台一样堆功能。</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-blue-50/90">
              这里的主流程应该很简单：先明确实验目的，再创建方案，运行时持续盯住风险，结束后快速得到结果解读和下一步建议。
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() => setShowCreateDialog(true)}
                className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-slate-900 transition hover:bg-slate-100"
              >
                开始一个新实验
              </button>
              <button
                onClick={() => setShowExperimentSelector(true)}
                className="rounded-lg border border-white/30 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
              >
                打开最近实验
              </button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            {[
              {
                icon: FlaskConical,
                title: '实验前',
                desc: '从目的出发创建方案，而不是直接填参数表。',
              },
              {
                icon: Microscope,
                title: '实验中',
                desc: '实时看进度、异常和关键节点，不必一直盯屏。',
              },
              {
                icon: Sparkles,
                title: '实验后',
                desc: '快速得到结果摘要、对比分析和下一步建议。',
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
      </motion.section>

      <motion.section variants={itemVariants} className="grid gap-4 lg:grid-cols-3">
        {[
          {
            title: '1. 明确目标',
            desc: '先说清是筛选、标定、验证还是复现，再进入具体方法。',
            action: '新建实验',
            onClick: () => setShowCreateDialog(true),
          },
          {
            title: '2. 盯住运行',
            desc: '需要看实时状态、日志和曲线时，进入运行中实验视图。',
            action: '查看运行中实验',
            onClick: () => navigate('/dashboard'),
          },
          {
            title: '3. 拿到结论',
            desc: '从最近实验继续分析、对比、诊断，而不是重新找入口。',
            action: '打开最近实验',
            onClick: () => setShowExperimentSelector(true),
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
      </motion.section>

      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.autohyseeker')}</p>
              <div className="flex items-center mt-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    systemStatus.autohyseeker ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="ml-2 text-sm font-medium">
                  {systemStatus.autohyseeker ? t('overview.online') : t('overview.offline')}
                </span>
              </div>
            </div>
            <Server className="h-8 w-8 text-blue-500" />
          </div>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.microhyseeker')}</p>
              <div className="flex items-center mt-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    systemStatus.microhyseeker ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="ml-2 text-sm font-medium">
                  {systemStatus.microhyseeker ? t('overview.connected') : t('overview.disconnected')}
                </span>
              </div>
            </div>
            <Activity className="h-8 w-8 text-green-500" />
          </div>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.database')}</p>
              <div className="flex items-center mt-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    systemStatus.database ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className="ml-2 text-sm font-medium">
                  {systemStatus.database ? t('overview.online') : t('overview.offline')}
                </span>
              </div>
            </div>
            <Database className="h-8 w-8 text-purple-500" />
          </div>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">{t('overview.agents')}</p>
              <p className="text-2xl font-bold mt-2">
                {systemStatus.agents.running}/{systemStatus.agents.total}
              </p>
              <p className="text-xs text-gray-500">{t('overview.running')}</p>
            </div>
            <Activity className="h-8 w-8 text-orange-500" />
          </div>
        </motion.div>
      </div>

      {/* Quick Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          variants={itemVariants}
          className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 text-white"
        >
          <p className="text-sm opacity-90">{t('overview.totalExperiments')}</p>
          <p className="text-3xl font-bold mt-2">{statistics.totalExperiments}</p>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 text-white"
        >
          <p className="text-sm opacity-90">{t('overview.todayExperiments')}</p>
          <p className="text-3xl font-bold mt-2">{statistics.todayExperiments}</p>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 text-white"
        >
          <p className="text-sm opacity-90">{t('overview.successRate')}</p>
          <div className="flex items-center mt-2">
            <p className="text-3xl font-bold">{statistics.successRate}%</p>
            {statistics.successTrend === 'up' && <TrendingUp className="ml-2 h-6 w-6" />}
            {statistics.successTrend === 'down' && <TrendingDown className="ml-2 h-6 w-6" />}
          </div>
        </motion.div>

        <motion.div
          variants={itemVariants}
          className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 text-white"
        >
          <p className="text-sm opacity-90">{t('overview.avgDuration')}</p>
          <p className="text-3xl font-bold mt-2">{statistics.avgDuration}</p>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activities */}
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
        >
          <h2 className="text-lg font-semibold mb-4 flex items-center">
            <Clock className="h-5 w-5 mr-2 text-blue-500" />
            {t('overview.recentActivities')}
          </h2>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {activities.length === 0 ? (
              <p className="text-gray-500 text-center py-8">{t('overview.noActivities')}</p>
            ) : (
              activities.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <div className={`p-2 rounded-lg ${getActivityColor(activity.type)}`}>
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
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          variants={itemVariants}
          className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
        >
          <h2 className="text-lg font-semibold mb-4">{t('overview.quickActions')}</h2>
          <div className="grid grid-cols-2 gap-4">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowCreateDialog(true)}
              className="flex flex-col items-center justify-center p-6 bg-blue-50 hover:bg-blue-100 rounded-xl transition-colors"
            >
              <Plus className="h-8 w-8 text-blue-600 mb-2" />
              <span className="text-sm font-medium text-blue-600">{t('overview.createExperiment')}</span>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/templates')}
              className="flex flex-col items-center justify-center p-6 bg-green-50 hover:bg-green-100 rounded-xl transition-colors"
            >
              <FileText className="h-8 w-8 text-green-600 mb-2" />
              <span className="text-sm font-medium text-green-600">{t('overview.viewTemplates')}</span>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleAnalyzeRecent}
              className="flex flex-col items-center justify-center p-6 bg-purple-50 hover:bg-purple-100 rounded-xl transition-colors"
            >
              <BarChart className="h-8 w-8 text-purple-600 mb-2" />
              <span className="text-sm font-medium text-purple-600">{t('overview.analyzeRecent')}</span>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleGetSuggestions}
              className="flex flex-col items-center justify-center p-6 bg-orange-50 hover:bg-orange-100 rounded-xl transition-colors"
            >
              <Lightbulb className="h-8 w-8 text-orange-600 mb-2" />
              <span className="text-sm font-medium text-orange-600">{t('overview.getSuggestions')}</span>
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowExperimentSelector(true)}
              className="flex flex-col items-center justify-center p-6 bg-cyan-50 hover:bg-cyan-100 rounded-xl transition-colors col-span-2"
            >
              <FolderOpen className="h-8 w-8 text-cyan-600 mb-2" />
              <span className="text-sm font-medium text-cyan-600">加载最近实验</span>
            </motion.button>
          </div>
        </motion.div>
      </div>

      {/* System Health Chart */}
      <motion.div
        variants={itemVariants}
        className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all duration-200 p-6 border border-slate-200"
      >
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <BarChart className="h-5 w-5 mr-2 text-blue-500" />
          {t('overview.systemHealth')}
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-sm text-gray-600 mb-2">{t('overview.cpuUsage')}</p>
            <div className="h-32 flex items-end space-x-1">
              {systemHealth.cpu.length > 0 ? (
                systemHealth.cpu.map((value, index) => (
                  <div
                    key={index}
                    className="flex-1 bg-blue-500 rounded-t"
                    style={{ height: `${value}%` }}
                  />
                ))
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                  {t('overview.noData')}
                </div>
              )}
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-2">{t('overview.memoryUsage')}</p>
            <div className="h-32 flex items-end space-x-1">
              {systemHealth.memory.length > 0 ? (
                systemHealth.memory.map((value, index) => (
                  <div
                    key={index}
                    className="flex-1 bg-green-500 rounded-t"
                    style={{ height: `${value}%` }}
                  />
                ))
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                  {t('overview.noData')}
                </div>
              )}
            </div>
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-2">{t('overview.apiResponseTime')}</p>
            <div className="h-32 flex items-end space-x-1">
              {systemHealth.apiResponseTime.length > 0 ? (
                systemHealth.apiResponseTime.map((value, index) => (
                  <div
                    key={index}
                    className="flex-1 bg-purple-500 rounded-t"
                    style={{ height: `${Math.min(value / 10, 100)}%` }}
                  />
                ))
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm">
                  {t('overview.noData')}
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {showCreateDialog && (
        <ExperimentCreateDialog
          onClose={() => setShowCreateDialog(false)}
          onSubmit={(experiment) => {
            navigate(`/experiments/${(experiment as Record<string, string>).exp_id}`);
          }}
        />
      )}

      {showExperimentSelector && (
        <ExperimentSelector
          isOpen={showExperimentSelector}
          onClose={() => setShowExperimentSelector(false)}
          onSelect={handleLoadExperiment}
        />
      )}
    </motion.div>
  );
}
