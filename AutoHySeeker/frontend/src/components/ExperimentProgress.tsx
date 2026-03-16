import type { ExperimentProgressState } from '@/api/types';
import { Activity, AlertTriangle, Clock3, FlaskConical, PlayCircle, Sparkles } from 'lucide-react';

interface Props {
  experiment: ExperimentProgressState;
}

const STATUS_CONFIG = {
  idle: {
    label: '待命',
    tone: 'text-slate-700 bg-slate-100 border-slate-200',
    barColor: 'bg-slate-400',
    pulse: false,
    summary: '当前没有明确运行中的实验，建议先从 step editor 创建并启动。',
  },
  running: {
    label: '运行中',
    tone: 'text-blue-700 bg-blue-100 border-blue-200',
    barColor: 'bg-blue-500',
    pulse: true,
    summary: '重点盯住当前 step、开始时间和是否长时间无进展。',
  },
  completed: {
    label: '已完成',
    tone: 'text-emerald-700 bg-emerald-100 border-emerald-200',
    barColor: 'bg-emerald-500',
    pulse: false,
    summary: '这次运行已结束，下一步应该先看结果和 AI 分析入口。',
  },
  failed: {
    label: '异常 / 失败',
    tone: 'text-red-700 bg-red-100 border-red-200',
    barColor: 'bg-red-500',
    pulse: false,
    summary: '这次运行出现异常，优先回看当前 step 和最近日志。',
  },
} as const;

function formatElapsed(seconds?: number): string {
  if (seconds === undefined) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function inferSource(runName?: string) {
  if (!runName) return '—';
  if (runName.toLowerCase().includes('template')) return 'template';
  if (runName.toLowerCase().includes('agent')) return 'agent';
  return 'manual';
}

function inferDescription(status: ExperimentProgressState['status'], currentStep?: string) {
  if (!currentStep) {
    return status === 'idle' ? '暂无运行上下文。' : '当前未返回 step 描述。';
  }
  if (currentStep.toLowerCase().includes('cycle')) {
    return '当前在连续采集 / 轮询阶段，建议同时看实时曲线和日志。';
  }
  return `当前系统报告正在执行：${currentStep}`;
}

export function ExperimentProgress({ experiment }: Props) {
  const cfg = STATUS_CONFIG[experiment.status];
  const startedAt = experiment.elapsedSeconds ? new Date(Date.now() - experiment.elapsedSeconds * 1000) : undefined;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-blue-600">运行中的实验卡片</p>
          <h3 className="mt-1 text-lg font-semibold text-slate-900">现在到底在跑什么</h3>
          <p className="mt-2 text-sm text-slate-600">{cfg.summary}</p>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${cfg.tone}`}>
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${cfg.pulse ? 'animate-pulse bg-current' : 'bg-current'}`} />
          {cfg.label}
        </span>
      </div>

      <div className="mt-5 rounded-2xl bg-slate-50 p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl bg-white p-3 shadow-sm">
            {experiment.status === 'failed' ? <AlertTriangle className="h-5 w-5 text-red-600" /> : experiment.status === 'running' ? <PlayCircle className="h-5 w-5 text-blue-600" /> : <FlaskConical className="h-5 w-5 text-slate-700" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h4 className="truncate text-base font-semibold text-slate-900">{experiment.runName ?? '暂无活动实验'}</h4>
              {experiment.runId && <span className="rounded-full bg-white px-2 py-0.5 font-mono text-[11px] text-slate-500">{experiment.runId}</span>}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">{inferDescription(experiment.status, experiment.currentStep)}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500">实验名</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{experiment.runName ?? '—'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500">当前 step</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{experiment.currentStep ?? '—'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500">状态</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{cfg.label}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500">开始时间</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{startedAt ? startedAt.toLocaleString('zh-CN') : '—'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500">来源 / 描述</p>
          <p className="mt-1 text-sm font-semibold text-slate-900">{inferSource(experiment.runName)} / {inferDescription(experiment.status, experiment.currentStep)}</p>
        </div>
      </div>

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <Activity className="h-3.5 w-3.5" />
            <span>执行进度</span>
          </div>
          <span className="font-semibold text-slate-700">{experiment.progressPercent}%</span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className={`h-full rounded-full transition-all duration-500 ${cfg.barColor}`} style={{ width: `${experiment.progressPercent}%` }} />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
        <div className="inline-flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> 已运行 {formatElapsed(experiment.elapsedSeconds)}</div>
        <div className="inline-flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" /> 下一步建议：{experiment.status === 'running' ? '盯住 step 是否超时' : '完成后进入详情页看分析入口'}</div>
      </div>
    </div>
  );
}
