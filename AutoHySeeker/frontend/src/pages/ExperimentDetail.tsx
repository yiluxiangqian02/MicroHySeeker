import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  Brain,
  CheckCircle,
  Clock,
  FlaskConical,
  Lightbulb,
  Play,
  Target,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface ExperimentStep {
  step_type: string;
  description: string;
  params: Record<string, unknown>;
}

interface Experiment {
  exp_id: string;
  name: string;
  description: string;
  status: 'created' | 'running' | 'completed' | 'failed';
  steps: ExperimentStep[];
  tags: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
  data: Array<{ x: number; y: number }>;
}

const STATUS_CONFIG: Record<string, { icon: ReactNode; label: string; tone: string; summary: string }> = {
  created: {
    icon: <Clock className="h-5 w-5" />,
    label: '待执行',
    tone: 'text-slate-700 bg-slate-100 border-slate-200',
    summary: '方案已准备好，下一步是确认设备状态后开始执行。',
  },
  running: {
    icon: <Play className="h-5 w-5 animate-pulse" />,
    label: '运行中',
    tone: 'text-blue-700 bg-blue-100 border-blue-200',
    summary: '实验正在执行，建议重点盯住曲线趋势和异常波动。',
  },
  completed: {
    icon: <CheckCircle className="h-5 w-5" />,
    label: '已完成',
    tone: 'text-emerald-700 bg-emerald-100 border-emerald-200',
    summary: '实验已完成，现在应该先看结果是否可解释，再决定是否扩参数或复现。',
  },
  failed: {
    icon: <AlertCircle className="h-5 w-5" />,
    label: '失败',
    tone: 'text-red-700 bg-red-100 border-red-200',
    summary: '实验未成功完成，建议优先检查关键参数设置、设备状态和实验前处理。',
  },
};

const METHOD_LABELS: Record<string, string> = {
  cv: 'CV',
  eis: 'EIS',
  ca: 'CA',
  cp: 'CP',
  lsv: 'LSV',
  dpv: 'DPV',
  sqv: 'SWV',
};

function formatDateTime(value?: string) {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN');
}

function formatValue(value: unknown) {
  if (typeof value === 'number') return Number.isInteger(value) ? `${value}` : value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  if (typeof value === 'string') return value;
  return JSON.stringify(value);
}

function humanizeParamKey(key: string) {
  const dict: Record<string, string> = {
    startVoltage: '起始电压',
    endVoltage: '终止电压',
    scanRate: '扫描速率',
    cycles: '循环次数',
    stepVoltage: '步进电压',
    quietTime: '静置时间',
    sensitivity: '灵敏度',
    startFreq: '起始频率',
    endFreq: '终止频率',
    amplitude: '振幅',
    dcVoltage: '直流偏压',
    pointsPerDecade: '每十倍频点数',
    integrationTime: '积分时间',
    voltage: '施加电压',
    duration: '持续时间',
    sampleInterval: '采样间隔',
    current: '施加电流',
    pulseAmplitude: '脉冲幅度',
    pulseWidth: '脉冲宽度',
    frequency: '频率',
    increment: '电位增量',
  };
  return dict[key] ?? key;
}

function inferGoal(experiment: Experiment) {
  const text = `${experiment.name} ${experiment.description} ${experiment.tags.join(' ')}`.toLowerCase();
  if (text.includes('标定') || text.includes('calibration')) return '本次目标偏向标定或定量响应确认。';
  if (text.includes('复现') || text.includes('reproduction')) return '本次目标偏向复现既有结果，重点看一致性。';
  if (text.includes('故障') || text.includes('诊断') || text.includes('排查')) return '本次目标偏向故障复查，重点是找出异常来源。';
  if (text.includes('筛选') || text.includes('screen')) return '本次目标偏向快速筛选条件，先找到值得继续放大的范围。';
  return '本次实验用于回答一个明确的科研问题，建议先确认曲线是否支持当前假设。';
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
  return `已采集 ${experiment.data.length} 个数据点，响应范围约为 ${min.toFixed(3)} ~ ${max.toFixed(3)}，整体变化幅度约 ${delta.toFixed(3)}。`;
}

function buildAiInterpretation(experiment: Experiment) {
  if (experiment.status === 'created') {
    return 'AI 解读将在实验开始并产生数据后出现。当前建议先确认方案是否覆盖你最关心的参数区间。';
  }
  if (experiment.status === 'running') {
    return 'AI 解读占位：实验运行中。后续应结合曲线形态、峰位/阻抗变化或稳定性趋势给出初步判断。';
  }
  if (experiment.status === 'failed') {
    return 'AI 解读占位：本次实验失败。后续应结合设备状态、参数范围、样品前处理和历史相似实验给出排查建议。';
  }
  return 'AI 解读占位：后续这里会给出结果摘要、关键异常点、与历史实验的对比，以及下一轮实验参数建议。';
}

function buildNextActions(experiment: Experiment) {
  if (experiment.status === 'created') {
    return [
      '确认电极、样品和设备状态后开始执行。',
      '如果这是首轮摸底，优先保持单变量设计，避免一上来把范围铺得太大。',
      '执行后进入本页回看结果摘要和 AI 解读。',
    ];
  }
  if (experiment.status === 'running') {
    return [
      '继续观察曲线是否出现超预期波动或平台漂移。',
      '记录当前样品批次与环境条件，便于后续对照。',
      '完成后优先判断结果是否足够支撑下一步放大或复现。',
    ];
  }
  if (experiment.status === 'failed') {
    return [
      '回查关键参数是否超出合理范围，尤其是电压窗口、频率区间和持续时间。',
      '检查设备连接、样品状态和实验前处理是否一致。',
      '建议补一个保守参数版本，用于确认问题来自设备还是方案本身。',
    ];
  }
  return [
    '先确认结果是否符合原始目标，再决定是否进入下一轮参数扩展。',
    '如果信号趋势明确，建议补重复组或对照组验证稳定性。',
    '如结果与预期不一致，下一步应做故障复查或缩小参数窗口重新验证。',
  ];
}

export function ExperimentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [executing, setExecuting] = useState(false);

  const fetchExperiment = async () => {
    try {
      const res = await fetch(`/api/experiments/detail/${id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setExperiment(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchExperiment();
  }, [id]);

  const handleExecute = async () => {
    if (!experiment) return;
    setExecuting(true);
    try {
      const res = await fetch(`/api/experiments/detail/${experiment.exp_id}/execute`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchExperiment();
      alert('实验已开始执行，建议留在本页持续关注进展。');
    } catch (err) {
      alert(err instanceof Error ? err.message : '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  const keyParamItems = useMemo(() => {
    if (!experiment?.steps.length) return [] as Array<{ label: string; value: string }>;
    const firstStep = experiment.steps[0];
    return Object.entries(firstStep.params)
      .slice(0, 6)
      .map(([key, value]) => ({ label: humanizeParamKey(key), value: formatValue(value) }));
  }, [experiment]);

  const timelineItems = useMemo(() => {
    if (!experiment) return [];
    return [
      { label: '创建实验', value: formatDateTime(experiment.created_at) },
      { label: '开始执行', value: formatDateTime(experiment.started_at) },
      { label: '完成/终止', value: formatDateTime(experiment.completed_at) },
    ];
  }, [experiment]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error || !experiment) {
    return (
      <div className="p-6">
        <div className="rounded-lg bg-red-50 p-4 text-red-600">{error || '实验不存在'}</div>
        <button onClick={() => navigate(-1)} className="mt-4 flex items-center gap-2 text-blue-600">
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
      </div>
    );
  }

  const statusConf = STATUS_CONFIG[experiment.status] ?? STATUS_CONFIG.created;
  const goalSummary = inferGoal(experiment);
  const resultSummary = buildResultSummary(experiment);
  const aiInterpretation = buildAiInterpretation(experiment);
  const nextActions = buildNextActions(experiment);
  const primaryMethod = experiment.steps[0]?.step_type;

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="mb-3 flex items-center gap-1 text-sm text-gray-500 transition hover:text-gray-700"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <p className="text-sm font-medium text-blue-600">实验工作页</p>
          <h2 className="mt-1 text-3xl font-bold text-slate-900">{experiment.name}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {experiment.description || '当前未填写额外说明。建议后续补充实验背景、假设或样品信息，便于回看。'}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${statusConf.tone}`}>
              {statusConf.icon}
              {statusConf.label}
            </span>
            {primaryMethod && (
              <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-medium text-blue-700">
                主要方法：{METHOD_LABELS[primaryMethod] ?? primaryMethod.toUpperCase()}
              </span>
            )}
            {experiment.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">
                {tag}
              </span>
            ))}
          </div>
        </div>

        {experiment.status === 'created' && (
          <button
            onClick={handleExecute}
            disabled={executing}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:bg-blue-400"
          >
            <Play className="h-4 w-4" />
            {executing ? '提交中...' : '开始执行这次实验'}
          </button>
        )}
      </div>

      <section className="grid gap-4 lg:grid-cols-[1.25fr,0.95fr]">
        <div className="rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-800 p-6 text-white">
          <div className="flex items-start gap-3">
            <Target className="mt-1 h-5 w-5 text-blue-200" />
            <div>
              <p className="text-sm font-medium text-blue-200">实验目标</p>
              <h3 className="mt-1 text-xl font-semibold">这次实验想回答什么问题？</h3>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-blue-50/90">{goalSummary}</p>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium text-slate-500">执行状态</p>
          <div className="mt-3 flex items-center gap-3">
            <div className={`rounded-full border p-3 ${statusConf.tone}`}>{statusConf.icon}</div>
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
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr,1.05fr,0.9fr]">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold text-slate-900">关键参数摘要</h3>
          </div>
          {keyParamItems.length > 0 ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {keyParamItems.map((item) => (
                <div key={item.label} className="rounded-xl bg-slate-50 px-4 py-3">
                  <p className="text-xs text-slate-500">{item.label}</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{item.value}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-4 rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">
              暂无可展示的关键参数。
            </div>
          )}

          {experiment.steps.length > 0 && (
            <div className="mt-5 border-t border-slate-100 pt-5">
              <p className="text-sm font-medium text-slate-700">实验步骤</p>
              <div className="mt-3 space-y-3">
                {experiment.steps.map((step, index) => (
                  <div key={`${step.step_type}-${index}`} className="rounded-xl border border-slate-200 p-4">
                    <div className="flex items-center gap-3">
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                        {index + 1}
                      </span>
                      <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                        {METHOD_LABELS[step.step_type] ?? step.step_type.toUpperCase()}
                      </span>
                      <span className="text-sm text-slate-700">{step.description || `步骤 ${index + 1}`}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-emerald-600" />
              <h3 className="text-lg font-semibold text-slate-900">结果摘要</h3>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{resultSummary}</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-violet-600" />
              <h3 className="text-lg font-semibold text-slate-900">AI 解读</h3>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{aiInterpretation}</p>
            <div className="mt-4 rounded-xl border border-dashed border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-700">
              这里已预留产品级位置，后续可直接接入真实 Agent 的实验总结、趋势判断与异常解释。
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <div className="flex items-center gap-2 text-amber-900">
            <Lightbulb className="h-5 w-5" />
            <h3 className="text-lg font-semibold">下一步建议</h3>
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

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">实验数据</h3>
        <p className="mt-1 text-sm text-slate-600">这里承接本次实验的原始数据或关键曲线，避免创建、执行、分析之间断开。</p>

        <div className="mt-5">
          {experiment.data.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={experiment.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="x" label={{ value: 'E / V', position: 'insideBottomRight', offset: -5 }} />
                <YAxis label={{ value: 'I / A', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Line type="monotone" dataKey="y" stroke="#2563EB" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-40 items-center justify-center rounded-xl border-2 border-dashed border-slate-200 text-sm text-slate-400">
              暂无数据{experiment.status === 'created' ? ' — 请先开始执行实验' : ''}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
