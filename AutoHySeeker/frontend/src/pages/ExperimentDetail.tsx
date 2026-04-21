import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { chatApi } from '../api/chat';
import toast from 'react-hot-toast';
import {
  AlertCircle,
  ArrowLeft,
  Beaker,
  Brain,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Droplets,
  FlaskConical,
  Lightbulb,
  Loader2,
  Play,
  ScrollText,
  Square,
  Target,
  Wind,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SkeletonList } from '@/components/Skeleton';
import { EmptyState } from '@/components/EmptyState';

interface ExperimentStep {
  step_type: string;
  description: string;
  params: Record<string, any>;
  parallel_group?: number;
}

interface StepProgress {
  status: 'running' | 'completed' | 'skipped' | 'stopped' | 'pending';
  started_at?: string;
  completed_at?: string;
}

interface ProgressData {
  exp_id: string;
  status: string;
  total_steps: number;
  current_step_index: number;
  current_step: ExperimentStep | null;
  next_step: ExperimentStep | null;
  step_status: string;
  step_started_at: string | null;
  progress_percent: number;
  elapsed_seconds: number;
  cancelled: boolean;
  step_progress?: StepProgress[];
  error_detail?: string | null;
  logs: Array<{ ts: string; level: string; message: string }>;
}

interface Experiment {
  exp_id: string;
  name: string;
  description: string;
  status: 'created' | 'running' | 'completed' | 'failed' | 'stopped';
  steps: ExperimentStep[];
  tags: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
  data: Array<{ x: number; y: number }>;
  step_progress?: StepProgress[];
  logs?: Array<{ ts: string; level: string; message: string }>;
  execution_source?: string;
}

const STATUS_CONFIG: Record<string, { icon: () => ReactNode; label: string; tone: string; summary: string }> = {
  created: {
    icon: () => <Clock className="h-5 w-5" />,
    label: '待执行',
    tone: 'text-slate-700 bg-slate-100 border-slate-200',
    summary: '方案已准备好，下一步是确认设备状态后开始执行。',
  },
  running: {
    icon: () => <Play className="h-5 w-5 animate-pulse" />,
    label: '运行中',
    tone: 'text-blue-700 bg-blue-100 border-blue-200',
    summary: '实验正在执行，建议关注当前步骤进度、曲线趋势和异常波动。',
  },
  completed: {
    icon: () => <CheckCircle className="h-5 w-5" />,
    label: '已完成',
    tone: 'text-emerald-700 bg-emerald-100 border-emerald-200',
    summary: '实验已完成，建议先确认结果是否符合预期，再决定是否扩展参数或复现实验。',
  },
  failed: {
    icon: () => <AlertCircle className="h-5 w-5" />,
    label: '失败',
    tone: 'text-red-700 bg-red-100 border-red-200',
    summary: '实验未成功完成，建议优先检查关键步骤参数、设备状态和实验前处理。',
  },
  stopped: {
    icon: () => <Square className="h-5 w-5" />,
    label: '已停止',
    tone: 'text-orange-700 bg-orange-100 border-orange-200',
    summary: '实验被手动停止，可查看已完成步骤的数据。',
  },
};

const STEP_TYPE_META: Record<string, { label: string; icon: () => ReactNode; tone: string }> = {
  prep_sol: {
    label: '配液',
    icon: () => <Beaker className="h-4 w-4" />,
    tone: 'bg-violet-50 text-violet-700 border-violet-200',
  },
  transfer: {
    label: '移液',
    icon: () => <FlaskConical className="h-4 w-4" />,
    tone: 'bg-sky-50 text-sky-700 border-sky-200',
  },
  flush: {
    label: '冲洗',
    icon: () => <Droplets className="h-4 w-4" />,
    tone: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  },
  echem: {
    label: '电化学',
    icon: () => <FlaskConical className="h-4 w-4" />,
    tone: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  blank: {
    label: '空白',
    icon: () => <Clock className="h-4 w-4" />,
    tone: 'bg-slate-50 text-slate-700 border-slate-200',
  },
  evacuate: {
    label: '排空',
    icon: () => <Wind className="h-4 w-4" />,
    tone: 'bg-amber-50 text-amber-700 border-amber-200',
  },
};

function formatDateTime(value?: string) {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN');
}

function formatElapsed(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatValue(value: unknown) {
  if (value == null || value === '') return '—';
  if (typeof value === 'number') return Number.isInteger(value) ? `${value}` : value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function inferGoal(experiment: Experiment) {
  const text = `${experiment.name} ${experiment.description} ${experiment.tags.join(' ')}`.toLowerCase();
  if (text.includes('标定') || text.includes('calibration')) return '本次目标偏向标定或定量响应确认。';
  if (text.includes('复现') || text.includes('reproduction')) return '本次目标偏向复现既有结果，重点看一致性。';
  if (text.includes('故障') || text.includes('诊断') || text.includes('排查')) return '本次目标偏向故障复查，重点是找出异常来源。';
  if (text.includes('筛选') || text.includes('screen')) return '本次目标偏向快速筛选条件，先找到值得继续放大的范围。';
  return '本次实验用于回答一个明确的科研问题，建议先确认步骤链是否覆盖你真正想验证的过程。';
}

function buildResultSummary(experiment: Experiment) {
  if (experiment.status === 'created') return '实验尚未开始，当前还没有结果。';
  if (experiment.status === 'running') return '实验正在进行，结果区会在采集到稳定数据后逐步有信息可看。';
  if (experiment.status === 'failed') return '实验未正常完成，当前应把注意力放在失败原因和排查路径上。';
  if (experiment.data.length === 0) return '实验已结束，但当前还没有可展示的数据。';

  const ys = experiment.data.map((point) => point.y);
  const min = Math.min(...ys);
  const max = Math.max(...ys);
  const delta = max - min;
  return `已采集 ${experiment.data.length} 个数据点，响应范围约 ${min.toFixed(3)} ~ ${max.toFixed(3)}，整体变化幅度约 ${delta.toFixed(3)}。`;
}

function buildAiInterpretation(experiment: Experiment) {
  if (experiment.status === 'created') {
    return 'AI 解读将在实验开始并产生数据后出现。当前建议先确认 step sequence 是否合理，尤其是配液、转移、冲洗和 echem 的衔接。';
  }
  if (experiment.status === 'running') {
    return 'AI 解读占位：实验运行中。后续应结合当前步骤、曲线形态、峰位 / 阻抗变化或稳定性趋势给出初步判断。';
  }
  if (experiment.status === 'failed') {
    return 'AI 解读占位：本次实验失败。后续应结合失败前一步、设备状态、参数范围和历史相似实验给出排查建议。';
  }
  return 'AI 解读占位：后续这里会给出结果摘要、关键异常点、与历史实验的对比，以及下一轮实验参数建议。';
}

function buildNextActions(experiment: Experiment) {
  if (experiment.status === 'created') {
    return [
      '确认电极、样品和设备状态后开始执行。',
      '检查步骤顺序是否合理，确认冲洗、配液、移液和电化学的编排顺序。',
      '执行后返回本页查看结果摘要和 AI 分析。',
    ];
  }
  if (experiment.status === 'running') {
    return [
      '继续观察当前步骤是否长时间无进展。',
      '记录当前样品批次与环境条件，便于后续对照。',
      '完成后优先判断结果是否足够支撑下一步放大或复现。',
    ];
  }
  if (experiment.status === 'failed') {
    return [
      '优先回查失败前一步的步骤类型和关键参数。',
      '检查设备连接、样品状态和实验前处理是否一致。',
      '建议补一个更保守的版本，用于确认问题来自设备还是方案本身。',
    ];
  }
  return [
    '先确认结果是否符合原始目标，再决定是否进入下一轮参数扩展。',
    '如果信号趋势明确，建议补重复组或对照组验证稳定性。',
    '如结果与预期不一致，下一步应做故障复查或缩小参数窗口重新验证。',
  ];
}

function summarizeStep(step: ExperimentStep) {
  const params = step.params ?? {};
  switch (step.step_type) {
    case 'prep_sol': {
      const prep = params.prep_sol_params ?? {};
      const selected = Object.entries(prep.selected_solutions ?? {})
        .filter(([, enabled]) => Boolean(enabled))
        .map(([name]) => name);
      return `${((prep.total_volume_ul ?? 0) / 1000).toFixed(1)} mL · ${selected.length ? selected.join(' / ') : '未选溶液'}`;
    }
    case 'transfer':
      return params.volume_ul ? `${params.volume_ul} μL · 泵${params.pump_address ?? '—'}` : `${params.transfer_duration ?? '—'} ${params.transfer_duration_unit ?? 's'} · 泵${params.pump_address ?? '—'}`;
    case 'flush':
      return `${params.flush_channel_id ?? '未选通道'} · ${params.flush_cycles ?? 1} 次循环`;
    case 'echem':
      return `${params.ec_settings?.technique ?? 'CV'} · 采样间隔 ${params.ec_settings?.sample_interval_ms ?? 100} ms`;
    case 'blank':
      return step.description || params.notes || '空白等待';
    case 'evacuate':
      return params.volume_ul ? `${params.volume_ul} μL 排空` : `${params.transfer_duration ?? '—'} ${params.transfer_duration_unit ?? 's'} 排空`;
    default:
      return step.description || '未配置';
  }
}

function getStepKeyFacts(step: ExperimentStep): Array<{ label: string; value: string }> {
  const params = step.params ?? {};
  switch (step.step_type) {
    case 'prep_sol': {
      const prep = params.prep_sol_params ?? {};
      const selected = Object.entries(prep.selected_solutions ?? {})
        .filter(([, enabled]) => Boolean(enabled))
        .map(([name]) => name)
        .join(', ');
      return [
        { label: '总体积', value: `${formatValue(prep.total_volume_ul)} μL` },
        { label: '已选溶液', value: selected || '—' },
      ];
    }
    case 'transfer':
    case 'evacuate':
      return [
        { label: '泵地址', value: formatValue(params.pump_address) },
        { label: '方向', value: formatValue(params.pump_direction) },
        { label: '转速', value: `${formatValue(params.pump_rpm)} RPM` },
        { label: '体积', value: params.volume_ul ? `${formatValue(params.volume_ul)} μL` : '—' },
        { label: '持续时间', value: params.transfer_duration ? `${formatValue(params.transfer_duration)} ${formatValue(params.transfer_duration_unit)}` : '—' },
      ];
    case 'flush':
      return [
        { label: '冲洗通道', value: formatValue(params.flush_channel_id) },
        { label: '转速', value: `${formatValue(params.flush_rpm)} RPM` },
        { label: '单次时长', value: `${formatValue(params.flush_cycle_duration_s)} s` },
        { label: '循环次数', value: formatValue(params.flush_cycles) },
      ];
    case 'echem': {
      const ec = params.ec_settings ?? {};
      return [
        { label: '测量技术', value: formatValue(ec.technique) },
        { label: '采样间隔', value: `${formatValue(ec.sample_interval_ms)} ms` },
        { label: '静置时间', value: `${formatValue(ec.quiet_time_s)} s` },
        { label: '关键参数', value: [ec.e0, ec.eh, ec.el, ec.ef].filter((item) => item !== undefined).map((item) => formatValue(item)).join(' / ') || '—' },
      ];
    }
    default:
      return [{ label: '备注', value: step.description || params.notes || '—' }];
  }
}

export function ExperimentDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [executing, setExecuting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [agentResponse, setAgentResponse] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [logsExpanded, setLogsExpanded] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchExperiment = useCallback(async () => {
    try {
      const res = await fetch(`/api/experiments/detail/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setExperiment(data);
      setError('');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t('experimentDetail.loading');
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [id, t]);

  const fetchProgress = useCallback(async () => {
    if (!id) return;
    try {
      const res = await fetch(`/api/experiments/detail/${id}/progress`);
      if (!res.ok) return;
      const data: ProgressData = await res.json();
      setProgress(data);
      // Sync status back to experiment
      if (experiment && data.status !== experiment.status) {
        setExperiment((prev) => prev ? { ...prev, status: data.status as Experiment['status'] } : prev);
      }
    } catch {
      // ignore polling errors
    }
  }, [id, experiment]);

  useEffect(() => {
    if (id) fetchExperiment();
  }, [id, fetchExperiment]);

  // Poll progress when experiment is running
  useEffect(() => {
    if (!experiment) return;
    // 运行中：实时轮询；刚完成/失败/停止：拉取一次最终状态
    if (experiment.status === 'running') {
      fetchProgress();
      const interval = setInterval(fetchProgress, 2000);
      return () => clearInterval(interval);
    }
    // 非 running 时也拉一次 progress 以获取 error_detail 和最终日志
    if (['completed', 'failed', 'stopped'].includes(experiment.status)) {
      fetchProgress();
    }
  }, [experiment?.status, fetchProgress]);

  // Auto-refresh experiment data when status changes from running
  useEffect(() => {
    if (progress && progress.status !== 'running' && experiment?.status === 'running') {
      fetchExperiment();
      // 失败时自动展开日志
      if (progress.status === 'failed') {
        setLogsExpanded(true);
      }
    }
  }, [progress?.status]);

  // Auto scroll logs
  useEffect(() => {
    if (logsExpanded && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [progress?.logs?.length, logsExpanded]);

  const handleExecute = async () => {
    if (!experiment) return;
    setExecuting(true);
    try {
      const res = await fetch(`/api/experiments/detail/${experiment.exp_id}/execute`, {
        method: 'POST',
      });
      if (!res.ok) {
        // 解析服务端结构化错误信息
        let detail = `HTTP ${res.status}`;
        try {
          const body = await res.json();
          detail = body.detail || detail;
        } catch { /* ignore */ }
        throw new Error(detail);
      }
      await fetchExperiment();
      toast.success('实验已开始执行，请留在本页关注进展');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '执行失败';
      toast.error(`启动失败: ${errorMsg}`, { duration: 6000 });
    } finally {
      setExecuting(false);
    }
  };

  const handleStop = async () => {
    if (!experiment) return;
    setStopping(true);
    try {
      const res = await fetch(`/api/experiments/detail/${experiment.exp_id}/stop`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success('正在停止实验...');
      setTimeout(() => fetchExperiment(), 2000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '停止失败';
      toast.error(errorMsg);
    } finally {
      setStopping(false);
    }
  };

  const handleAnalyze = async (promptType: string) => {
    if (!id) return;
    setAnalyzing(true);
    setAgentResponse(null);
    try {
      let message = '请分析当前实验：\n';
      if (promptType === 'data') {
        message += '重点对结果做摘要、关键指标提取、图表与对比分析。';
      } else {
        message += '提供文献上下文、历史实验对比，以及下一轮改进方案的建议。';
      }
      
      const res = await chatApi.analyzeExperiment(id, message);
      setAgentResponse(res.message || 'Agent 请求成功，但未返回实际内容。');
      toast.success('分析完成');
    } catch (err) {
      const errorMsg = `分析失败: ${err instanceof Error ? err.message: '网络异常'}`;
      setAgentResponse(errorMsg);
      toast.error(errorMsg);
    } finally {
      setAnalyzing(false);
    }
  };

  const currentStepIndex = progress?.current_step_index ?? 0;
  const currentStep = useMemo(() => {
    if (progress?.current_step) return progress.current_step;
    return experiment?.steps?.[0] ?? null;
  }, [experiment, progress]);
  const timelineItems = useMemo(() => {
    if (!experiment) return [];
    return [
      { label: '创建实验', value: formatDateTime(experiment.created_at) },
      { label: '开始执行', value: formatDateTime(experiment.started_at) },
      { label: '完成/终止', value: formatDateTime(experiment.completed_at) },
    ];
  }, [experiment]);

  const progressPercent = progress?.progress_percent ?? 0;
  const elapsedSeconds = progress?.elapsed_seconds ?? 0;
  const logs = progress?.logs ?? experiment?.logs ?? [];

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <SkeletonList count={2} />
      </div>
    );
  }

  if (error || !experiment) {
    return (
      <div className="p-6">
        <EmptyState
          icon={<AlertCircle className="h-12 w-12 text-red-400" />}
          title={t('experimentDetail.notFound')}
          subtitle={error || '实验不存在'}
          action={
            <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-blue-600 hover:underline">
              <ArrowLeft className="h-4 w-4" />
              {t('experimentDetail.goBack')}
            </button>
          }
        />
      </div>
    );
  }

  const statusConf = STATUS_CONFIG[experiment.status] ?? STATUS_CONFIG.created;
  const goalSummary = inferGoal(experiment);
  const resultSummary = buildResultSummary(experiment);
  const aiInterpretation = buildAiInterpretation(experiment);
  const nextActions = buildNextActions(experiment);

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <button onClick={() => navigate(-1)} className="mb-3 flex items-center gap-1 text-sm text-gray-500 transition hover:text-gray-700">
            <ArrowLeft className="h-4 w-4" />
            {t('experimentDetail.goBack')}
          </button>
          <p className="text-sm font-medium text-blue-600">{t('experimentDetail.title')}</p>
          <h2 className="mt-1 text-3xl font-bold text-slate-900">{experiment.name}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {experiment.description || t('experimentDetail.noDescription')}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${statusConf.tone}`}>
              {statusConf.icon()}
              {statusConf.label}
            </span>
            {experiment.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="flex gap-3">
          {(experiment.status === 'created' || experiment.status === 'failed' || experiment.status === 'stopped') && (
            <button
              onClick={handleExecute}
              disabled={executing}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:bg-blue-400"
            >
              <Play className="h-4 w-4" />
              {executing ? t('experimentDetail.submitting') : (
                experiment.status === 'created' ? t('experimentDetail.startExecuting') : '重新执行'
              )}
            </button>
          )}
          {experiment.status === 'running' && (
            <button
              onClick={handleStop}
              disabled={stopping}
              className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-red-700 disabled:bg-red-400"
            >
              <Square className="h-4 w-4" />
              {stopping ? '停止中...' : '停止实验'}
            </button>
          )}
        </div>
      </div>

      <section className="grid gap-4 lg:grid-cols-[1.25fr,0.95fr]">
        <div className="rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-800 p-6 text-white">
          <div className="flex items-start gap-3">
            <Target className="mt-1 h-5 w-5 text-blue-200" />
            <div>
              <p className="text-sm font-medium text-blue-200">{t('experimentDetail.goalTitle')}</p>
              <h3 className="mt-1 text-xl font-semibold">{t('experimentDetail.goalQuestion')}</h3>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-blue-50/90">{goalSummary}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium text-slate-500">{t('experimentDetail.executionStatus')}</p>
          <div className="mt-3 flex items-center gap-3">
            <div className={`rounded-full border p-3 ${statusConf.tone}`}>{statusConf.icon()}</div>
            <div>
              <p className="text-lg font-semibold text-slate-900">{statusConf.label}</p>
              <p className="text-sm text-slate-600">{statusConf.summary}</p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            {timelineItems.map((item) => (
              <div key={item.label} className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-slate-500">{item.label}</p>
                <p className="mt-1 text-sm font-medium text-slate-900">{item.value}</p>
              </div>
            ))}
          </div>

          {experiment.status === 'running' && (
            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
                <span>执行进度 · 步骤 {currentStepIndex + 1}/{experiment.steps.length}</span>
                <span className="font-semibold text-slate-700">{progressPercent}%</span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
                <Clock className="h-3.5 w-3.5" />
                <span>已运行 {formatElapsed(elapsedSeconds)}</span>
                {progress?.next_step && (
                  <span className="ml-auto">下一步: {STEP_TYPE_META[progress.next_step.step_type]?.label ?? progress.next_step.step_type}</span>
                )}
              </div>
            </div>
          )}

          {/* 失败/停止时显示错误详情横幅 */}
          {(experiment.status === 'failed' || experiment.status === 'stopped') && (
            <div className={`mt-5 rounded-xl border p-4 ${
              experiment.status === 'failed'
                ? 'border-red-200 bg-red-50 text-red-800'
                : 'border-orange-200 bg-orange-50 text-orange-800'
            }`}>
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="text-sm">
                  <p className="font-medium">
                    {experiment.status === 'failed' ? '实验执行失败' : '实验已被停止'}
                  </p>
                  {progress?.error_detail && (
                    <p className="mt-1 text-xs opacity-80">{progress.error_detail}</p>
                  )}
                  <p className="mt-2 text-xs opacity-70">可点击「重新执行」按钮再次运行，或展开日志查看详情。</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr,1.05fr,0.9fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-slate-900">{t('experimentDetail.runningContext')}</h3>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-slate-50 px-4 py-3">
              <p className="text-xs text-slate-500">{t('experimentDetail.totalSteps')}</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{experiment.steps.length}</p>
            </div>
            <div className="rounded-xl bg-slate-50 px-4 py-3">
              <p className="text-xs text-slate-500">{t('experimentDetail.currentStep')}</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{currentStep ? summarizeStep(currentStep) : '—'}</p>
            </div>
          </div>

          {currentStep && (
            <div className="mt-5 rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${STEP_TYPE_META[currentStep.step_type]?.tone ?? 'bg-slate-50 text-slate-700 border-slate-200'}`}>
                  {STEP_TYPE_META[currentStep.step_type]?.icon()}
                  {STEP_TYPE_META[currentStep.step_type]?.label ?? currentStep.step_type}
                </span>
              </div>
              <p className="mt-3 text-sm text-slate-700">{currentStep.description || summarizeStep(currentStep)}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {getStepKeyFacts(currentStep).map((item) => (
                  <div key={item.label} className="rounded-xl bg-slate-50 px-4 py-3">
                    <p className="text-xs text-slate-500">{item.label}</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {experiment.steps.length > 0 && (
            <div className="mt-5 border-t border-slate-100 pt-5">
              <p className="text-sm font-medium text-slate-700">{t('experimentDetail.stepChain')}</p>
              <div className="mt-3 space-y-3">
                {(() => {
                  const rendered: React.ReactNode[] = [];
                  let i = 0;
                  while (i < experiment.steps.length) {
                    const step = experiment.steps[i];
                    const pg = step.parallel_group ?? step.params?.parallel_group ?? 0;

                    // Collect consecutive steps with the same non-zero parallel_group
                    if (pg > 0) {
                      const groupSteps: { step: ExperimentStep; index: number }[] = [];
                      while (i < experiment.steps.length && ((experiment.steps[i].parallel_group ?? experiment.steps[i].params?.parallel_group ?? 0) === pg)) {
                        groupSteps.push({ step: experiment.steps[i], index: i });
                        i++;
                      }
                      rendered.push(
                        <div key={`pg-${pg}-${groupSteps[0].index}`} className="rounded-xl border-2 border-dashed border-indigo-300 bg-indigo-50/30 p-3">
                          <div className="mb-2 flex items-center gap-2">
                            <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700">
                              ∥{pg}
                            </span>
                            <span className="text-xs text-indigo-600 font-medium">并行组 · {groupSteps.length} 步同时执行</span>
                          </div>
                          <div className="space-y-2">
                            {groupSteps.map(({ step: gs, index: gi }) => {
                              const stepProg = progress?.step_progress?.[gi] ?? experiment.step_progress?.[gi];
                              const isCurrent = experiment.status === 'running' && gi === currentStepIndex;
                              const isCompleted = stepProg?.status === 'completed';
                              const isSkipped = stepProg?.status === 'skipped';

                              let stepBorder = 'border-slate-200';
                              let stepBg = 'bg-white';
                              let numberStyle = 'bg-slate-100 text-slate-600';
                              if (isCurrent) { stepBorder = 'border-blue-400'; stepBg = 'bg-blue-50/40'; numberStyle = 'bg-blue-600 text-white animate-pulse'; }
                              else if (isCompleted) { numberStyle = 'bg-emerald-500 text-white'; }
                              else if (isSkipped) { numberStyle = 'bg-orange-400 text-white'; }

                              return (
                                <div key={`${gs.step_type}-${gi}`} className={`rounded-lg border ${stepBorder} ${stepBg} p-3`}>
                                  <div className="flex flex-wrap items-center gap-3">
                                    <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${numberStyle}`}>
                                      {isCompleted ? '✓' : isSkipped ? '–' : gi + 1}
                                    </span>
                                    <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${STEP_TYPE_META[gs.step_type]?.tone ?? 'bg-slate-50 text-slate-700 border-slate-200'}`}>
                                      {STEP_TYPE_META[gs.step_type]?.icon()}
                                      {STEP_TYPE_META[gs.step_type]?.label ?? gs.step_type}
                                    </span>
                                    <span className="text-sm text-slate-700">{gs.description || summarizeStep(gs)}</span>
                                    {isCurrent && <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-blue-600"><Loader2 className="h-3 w-3 animate-spin" /> 执行中</span>}
                                    {isCompleted && <span className="ml-auto text-xs text-emerald-600">✓ 完成</span>}
                                    {isSkipped && <span className="ml-auto text-xs text-orange-600">跳过</span>}
                                  </div>
                                  <p className="mt-1 text-xs text-slate-500">{summarizeStep(gs)}</p>
                                </div>
                              );
                            })}
                          </div>
                        </div>,
                      );
                    } else {
                      // Serial step (parallel_group === 0)
                      const stepProg = progress?.step_progress?.[i] ?? experiment.step_progress?.[i];
                      const isCurrent = experiment.status === 'running' && i === currentStepIndex;
                      const isCompleted = stepProg?.status === 'completed';
                      const isSkipped = stepProg?.status === 'skipped';

                      let stepBorder = 'border-slate-200';
                      let stepBg = '';
                      let numberStyle = 'bg-slate-100 text-slate-600';
                      if (isCurrent) { stepBorder = 'border-blue-400'; stepBg = 'bg-blue-50/40'; numberStyle = 'bg-blue-600 text-white animate-pulse'; }
                      else if (isCompleted) { numberStyle = 'bg-emerald-500 text-white'; }
                      else if (isSkipped) { numberStyle = 'bg-orange-400 text-white'; }

                      rendered.push(
                        <div key={`${step.step_type}-${i}`} className={`rounded-xl border ${stepBorder} ${stepBg} p-4`}>
                          <div className="flex flex-wrap items-center gap-3">
                            <span className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${numberStyle}`}>
                              {isCompleted ? '✓' : isSkipped ? '–' : i + 1}
                            </span>
                            <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-medium ${STEP_TYPE_META[step.step_type]?.tone ?? 'bg-slate-50 text-slate-700 border-slate-200'}`}>
                              {STEP_TYPE_META[step.step_type]?.icon()}
                              {STEP_TYPE_META[step.step_type]?.label ?? step.step_type}
                            </span>
                            <span className="text-sm text-slate-700">{step.description || summarizeStep(step)}</span>
                            {isCurrent && <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-blue-600"><Loader2 className="h-3 w-3 animate-spin" /> 执行中</span>}
                            {isCompleted && <span className="ml-auto text-xs text-emerald-600">✓ 完成</span>}
                            {isSkipped && <span className="ml-auto text-xs text-orange-600">跳过</span>}
                          </div>
                          <p className="mt-2 text-xs text-slate-500">{summarizeStep(step)}</p>
                        </div>,
                      );
                      i++;
                    }
                  }
                  return rendered;
                })()}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-emerald-600" />
              <h3 className="text-lg font-semibold text-slate-900">{t('experimentDetail.resultSummary')}</h3>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{resultSummary}</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-violet-600" />
              <h3 className="text-lg font-semibold text-slate-900">{t('experimentDetail.agentResponse')}</h3>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{aiInterpretation}</p>
            
            {analyzing ? (
              <div className="mt-4 flex items-center justify-center p-6 text-violet-600">
                <div className="flex flex-col items-center gap-2">
                  <Play className="h-6 w-6 animate-spin opacity-70" style={{ animationDirection: 'reverse' }} />
                  <span className="text-sm font-medium">{t('experimentDetail.analyzing')}</span>
                </div>
              </div>
            ) : agentResponse ? (
              <div className="mt-4 rounded-xl border border-violet-200 bg-violet-50/50 p-4">
                <div className="flex items-start justify-between">
                  <h4 className="text-sm font-semibold text-violet-900">{t('experimentDetail.analysisResult')}</h4>
                  <button 
                    onClick={() => setAgentResponse(null)}
                    className="text-xs text-violet-600 hover:text-violet-800"
                  >
                    {t('experimentDetail.clear')}
                  </button>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{agentResponse}</p>
              </div>
            ) : (
              <>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <button 
                    onClick={() => handleAnalyze('data')}
                    className="rounded-xl border border-violet-200 bg-violet-50 px-4 py-3 text-left text-sm text-violet-800 transition hover:bg-violet-100"
                  >
                    <div className="font-semibold">{t('experimentDetail.dataAssistant')}</div>
                    <div className="mt-1 text-xs leading-5 text-violet-700">{t('experimentDetail.dataAssistantDesc')}</div>
                  </button>
                  <button 
                    onClick={() => handleAnalyze('knowledge')}
                    className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-left text-sm text-blue-800 transition hover:bg-blue-100"
                  >
                    <div className="font-semibold">{t('experimentDetail.knowledgeAssistant')}</div>
                    <div className="mt-1 text-xs leading-5 text-blue-700">{t('experimentDetail.knowledgeAssistantDesc')}</div>
                  </button>
                </div>
                <div className="mt-4 rounded-xl border border-dashed border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-700">
                  {t('experimentDetail.agentSimDesc')}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <div className="flex items-center gap-2 text-amber-900">
            <Lightbulb className="h-5 w-5" />
            <h3 className="text-lg font-semibold">{t('experimentDetail.nextSteps')}</h3>
          </div>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-amber-900">
            {nextActions.map((item) => (
              <li key={item} className="flex gap-2">
                <span>•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Execution Logs Panel */}
      {logs.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <button
            onClick={() => setLogsExpanded(!logsExpanded)}
            className="flex w-full items-center justify-between p-5 text-left"
          >
            <div className="flex items-center gap-2">
              <ScrollText className="h-5 w-5 text-slate-600" />
              <h3 className="text-lg font-semibold text-slate-900">执行日志</h3>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{logs.length}</span>
              <span className="text-[10px] text-slate-300 font-mono">💾 data/experiments.json</span>
            </div>
            {logsExpanded ? <ChevronUp className="h-5 w-5 text-slate-400" /> : <ChevronDown className="h-5 w-5 text-slate-400" />}
          </button>
          {logsExpanded && (
            <div className="max-h-80 overflow-y-auto border-t border-slate-100 px-5 pb-4">
              <div className="space-y-1 pt-3 font-mono text-xs">
                {logs.map((log, i) => {
                  const levelColor =
                    log.level === 'error' ? 'text-red-600' :
                    log.level === 'warn' ? 'text-orange-600' :
                    'text-slate-600';
                  return (
                    <div key={i} className={`flex gap-3 ${levelColor}`}>
                      <span className="shrink-0 text-slate-400">{new Date(log.ts).toLocaleTimeString('zh-CN')}</span>
                      <span className="shrink-0 w-12 text-right font-semibold uppercase">{log.level}</span>
                      <span className="break-all">{log.message}</span>
                    </div>
                  );
                })}
                <div ref={logsEndRef} />
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
