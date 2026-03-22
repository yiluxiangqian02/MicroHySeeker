import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Filter,
  Play,
  Search,
} from 'lucide-react';
import { useExperimentsListQuery } from '../hooks/useExperimentsListQuery';
import type { Experiment } from '../api/experiments';

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; label: string; tone: string }> = {
  created: {
    icon: <Clock className="h-4 w-4" />,
    label: '待执行',
    tone: 'bg-slate-100 text-slate-700',
  },
  running: {
    icon: <Play className="h-4 w-4 animate-pulse" />,
    label: '运行中',
    tone: 'bg-blue-100 text-blue-700',
  },
  completed: {
    icon: <CheckCircle className="h-4 w-4" />,
    label: '已完成',
    tone: 'bg-emerald-100 text-emerald-700',
  },
  failed: {
    icon: <AlertCircle className="h-4 w-4" />,
    label: '失败',
    tone: 'bg-red-100 text-red-700',
  },
};

export function Experiments() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: experiments = [], isLoading, error } = useExperimentsListQuery();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredExperiments = useMemo(() => {
    return experiments.filter((exp) => {
      const matchSearch =
        exp.name.toLowerCase().includes(search.toLowerCase()) ||
        exp.description.toLowerCase().includes(search.toLowerCase()) ||
        exp.tags.some((tag) => tag.toLowerCase().includes(search.toLowerCase()));
      const matchStatus = statusFilter === 'all' || exp.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [experiments, search, statusFilter]);

  function formatTime(value?: string) {
    if (!value) return '—';
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function summarizeCurrentStep(exp: Experiment) {
    const current = exp.steps?.[0];
    if (!current) return t('experiments.noStepInfo');
    return `${current.step_type}${current.description ? ` · ${current.description}` : ''}`;
  }

  return (
    <div className="flex h-full flex-col p-6 lg:p-8">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">{t('nav.experiments')}</h1>
          <p className="mt-2 text-sm text-slate-500">
            {t('experiments.subtitle')}
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-slate-500">{t('common.loading')}</div>
        </div>
      ) : error ? (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-red-500">{t('common.error')}</div>
        </div>
      ) : (
        <div className="flex flex-col gap-6 flex-1">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder={t('experiments.searchPlaceholder')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-10 pr-4 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="relative sm:w-48">
              <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full appearance-none rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-8 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              >
                <option value="all">{t('experiments.statusAll')}</option>
                <option value="created">{t('experiments.statusCreated')}</option>
                <option value="running">{t('experiments.statusRunning')}</option>
                <option value="completed">{t('experiments.statusCompleted')}</option>
                <option value="failed">{t('experiments.statusFailed')}</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 select-none">
            {filteredExperiments.map((exp) => {
              const status = STATUS_CONFIG[exp.status] || STATUS_CONFIG.created;
              return (
                <div
                  key={exp.exp_id}
                  onClick={() => navigate(`/experiments/${exp.exp_id}`)}
                  className="group relative flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium ${status.tone}`}
                    >
                      {status.icon}
                      {status.label}
                    </span>
                    <span className="text-xs text-slate-400">{formatTime(exp.created_at)}</span>
                  </div>

                  <h3 className="mt-4 truncate text-base font-semibold text-slate-900" title={exp.name}>
                    {exp.name}
                  </h3>

                  <p className="mt-2 line-clamp-2 text-xs text-slate-500" title={exp.description}>
                    {exp.description || t('experiments.noDescription')}
                  </p>

                  <div className="mt-4 mt-auto border-t border-slate-100 pt-4">
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-500">{t('experiments.currentStep')}</span>
                      <span className="truncate pl-2 text-slate-700" title={summarizeCurrentStep(exp)}>
                        {summarizeCurrentStep(exp)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
            
            {filteredExperiments.length === 0 && (
               <div className="col-span-full py-12 text-center text-slate-500">
                 {t('experiments.notFound')}
               </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}