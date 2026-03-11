import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  Clock,
  FileSearch,
  FlaskConical,
  Lightbulb,
  Play,
  Sparkles,
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

const STEP_TYPE_LABELS: Record<string, string> = {
  cv: 'CV',
  eis: 'EIS',
  ca: 'CA',
  cp: 'CP',
  lsv: 'LSV',
  dpv: 'DPV',
  sqv: 'SWV',
};

const STATUS_CONFIG: Record<string, { icon: ReactNode; label: string; color: string; summary: string }> = {
  created: {
    icon: <Clock className="h-5 w-5" />,
    label: '待执行',
    color: 'text-slate-700 bg-slate-100',
    summary: '实验方案已准备好，下一步建议检查关键参数后开始执行。',
  },
  running: {
    icon: <Play className="h-5 w-5 animate-pulse" />,
    label: '执行中',
    color: 'text-blue-700 bg-blue-100',
    summary: '实验正在推进，优先关注当前状态、实时曲线和异常信号。',
  },
  completed: {
    icon: <CheckCircle className="h-5 w-5" />,
    label: '已完成',
    color: 'text-emerald-700 bg-emerald-100',
    summary: '实验已完成，下一步应先看结果形态，再决定是否复现、扩参数或做对照。',
  },
  failed: {
    icon: <AlertCircle className="h-5 w-5" />,
    label: '执行失败',
    color: 'text-red-700 bg-red-100',
    summary: '实验未顺利完成，建议回看关键参数与设备状态，并进入故障排查路径。',
  },
};

function formatDateTime(value?: string) {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN');
}

function formatParamValue(value: unknown) {
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
  if (typeof value === 'string') return value;
  return '—';
}

function inferGoal(experiment: Experiment) {
  if (experiment.description?.trim()) return experiment.description.trim();
  const tags = experiment.tags ?? [];
  if (tags.length > 0) return `本次实验聚焦 ${tags.join(' / ')}。`;
  return '本次实验的目标尚未补充，建议在回顾时补上实验目的与判定标准。';
}

function buildParameterSummary(experiment: Experiment) {
  return experiment.steps.flatMap((step, stepIndex) =>
    Object.entries(step.params ?? {}).slice(0, 4).map(([key, value]) => ({
      id: `${stepIndex}-${key}`,
      stepIndex,
      method: STEP_TYPE_LABELS[step.step_type] ?? step.step_type.toUpperCase(),
      label: key,
      value: formatParamValue(value),
    })),
  );
}

function buildAiInterpretation(experiment: Experiment) {
  if (experiment.status === 'completed' && experiment.data.length > 0) {
    return [
      '已获得可用于初步判断的实验数据，建议先确认曲线整体形态是否与预期机制一致。',
      '如果峰位、阻抗弧或时间响应与历史经验明显偏离，优先排查样品状态、窗口设置和重复性。',
      '下一步适合补充对照组、重复组，或把本次结果与最近实验做并排比较。',
    ];
  }

  if (experiment.status === 'running') {
    return [
      '当前更重要的是观察实验是否按预期推进，而不是急着下结论。',
      '建议盯住实时曲线是否出现异常漂移、噪声升高或响应中断。',
      '实验完成后应第一时间回到此页，补上结果摘要与下一步动作。',
    ];
  }

  if (experiment.status === 'failed') {
    return [
      '当前结论应聚焦“为什么失败”，而不是强行解释数据。',
      '优先检查关键参数是否越界、步骤是否匹配实验目标，以及设备连接/状态是否稳定。',
      '建议下一步补做一轮更保守的验证实验，缩短时长并减少变量。',
    ];
  }

  return [
    '实验尚未开始，当前 AI 解读更适合做执行前预判。',
    '先确认本次参数是否足以回答目标问题，再开始执行。',
    '如这是首轮摸底实验，建议先做保守设置，重点确认趋势是否存在。',
  ];
}

function buildNextActions(experiment: Experiment) {
  if (experiment.status === 'completed') {
    return [
      '把本次结果与最近一次同方法实验做对比，确认变化是真趋势还是偶然波动。',
      '若结果符合预期，下一步可扩展参数范围或增加重复组。',
      '若结果有信号但不够稳定，优先优化一个关键参数，不要一次改太多。',
    ];
  }

  if (experiment.status === 'running') {
    return [
      '持续观察当前状态与曲线，必要时转到运行中视图查看实时细节。',
      '记录任何异常节点，便于实验结束后快速回顾。',
      '实验一结束，回到此页补做结果判断和下一轮计划。',
    ];
  }

  if (experiment.status === 'failed') {
    return [
      '优先回看关键参数和设备状态，确认是否存在设置过激或连接异常。',
      '建议做一轮短时、低风险的验证实验，快速判断问题是方法还是样品。',
      '如仍异常，再进入 AI 助手页做更细的故障排查。',
    ];
  }

  return [
    '确认方案后直接开始执行，避免长时间停留在“已创建”状态。',
    '如果是首轮摸底，建议先保持单步实验，拿到第一版可读数据。',
    '执行完成后，本页会成为结果解读和下一步建议的承接页。',
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
      const res = await fetch(`/api/experiments/detail/${experiment.exp_id}/execute`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchExperiment();
      alert('实验已开始执行，接下来优先关注状态和实时曲线。');
    } catch (err) {
      alert(err instanceof Error ? err.message : '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  const parameterSummary = useMemo(() => (experiment ? buildParameterSummary(experiment) : []), [experiment]);
  const aiInterpretation = useMemo(() => (experiment ? buildAiInterpretation(experiment) : []), [experiment]);
  const nextActions = useMemo(() => (experiment ? buildNextActions(experiment) : []), [experiment]);

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
  const goalText = inferGoal(experiment);

  return (
    <div className="space-y-6 p-6">
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-900 via-blue-900 to-cyan-800 p-6 text-white shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <button
              onClick={() => navigate(-1)}
              className="mb-3 flex items-center gap-1 text-sm text-blue-100 transition hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              返回
            </button>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-100">Experiment Loop Page</p>
            <h1 className="mt-3 text-3xl font-bold">{experiment.name}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-blue-50/90">{goalText}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${statusConf.color}`}>
                {statusConf.icon}
                {statusConf.label}
              </span>
              {experiment.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-white/10 px-2.5 py-1 text-xs text-blue-50">
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:min-w-[240px]">
            {experiment.status === 'created' && (
              <button
                onClick={handleExecute}
                disabled={executing}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-medium text-slate-900 transition hover:bg-slate-100 disabled:bg-slate-300"
              >
                <Play className="h-4 w-4" />
                {executing ? '提交中...' : '开始执行实验'}
              </button>
            )}
            <button
              onClick={() => navigate('/dashboard')}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/20 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/10"
            >
              <FlaskConical className="h-4 w-4" />
              查看运行中实验
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Target className="h-4 w-4 text-blue-600" />
            实验目标
          </div>
          <p className="mt-3 text-sm leading-7 text-slate-600">{goalText}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Clock className="h-4 w-4 text-blue-600" />
            当前状态
          </div>
          <p className="mt-3 text-lg font-semibold text-slate-900">{statusConf.label}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{statusConf.summary}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <FileSearch className="h-4 w-4 text-blue-600" />
            时间节点
          </div>
          <div className="mt-3 space-y-2 text-sm text-slate-600">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">创建时间</p>
              <p className="mt-1 text-slate-800">{formatDateTime(experiment.created_at)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">开始时间</p>
              <p className="mt-1 text-slate-800">{formatDateTime(experiment.started_at)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">完成时间</p>
              <p className="mt-1 text-slate-800">{formatDateTime(experiment.completed_at)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.35fr,0.95fr]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">关键参数摘要</h2>
            {parameterSummary.length > 0 ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {parameterSummary.map((item) => (
                  <div key={item.id} className="rounded-xl bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm text-slate-500">{item.method} · {item.label}</span>
                      <span className="text-sm font-medium text-slate-900">{item.value}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-xl border-2 border-dashed border-slate-200 p-6 text-sm text-slate-500">
                暂无参数摘要，建议后续把关键参数沉淀为结构化信息。
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">执行状态与步骤轨迹</h2>
            {experiment.steps.length > 0 ? (
              <div className="mt-4 space-y-3">
                {experiment.steps.map((step, i) => (
                  <div key={`${step.step_type}-${i}`} className="flex gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700">
                      {i + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                          {STEP_TYPE_LABELS[step.step_type] ?? step.step_type.toUpperCase()}
                        </span>
                        <span className="text-sm font-medium text-slate-900">
                          {step.description || `第 ${i + 1} 步`}
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        {i === 0
                          ? '这是本次实验的起始步骤，建议优先确认该步骤是否真正回答实验目标。'
                          : '如本步属于补充验证，建议只改少量关键参数，便于解释差异。'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-xl border-2 border-dashed border-slate-200 p-6 text-sm text-slate-500">
                暂无实验步骤。
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">结果区域</h2>
            {experiment.data.length > 0 ? (
              <div className="mt-4">
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={experiment.data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="x" label={{ value: 'E / V', position: 'insideBottomRight', offset: -5 }} />
                    <YAxis label={{ value: 'I / A', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="y" stroke="#3B82F6" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="mt-4 rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center">
                <p className="text-base font-medium text-slate-700">结果占位</p>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  {experiment.status === 'created'
                    ? '实验尚未开始，执行后这里会承接原始数据和结果图。'
                    : experiment.status === 'running'
                    ? '实验正在进行中，完成后这里会展示可回看的结果曲线。'
                    : '当前还没有可展示的数据，建议检查执行结果或补做一轮验证实验。'}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-violet-200 bg-violet-50 p-6 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-semibold text-violet-900">
              <Sparkles className="h-4 w-4" />
              AI 解读占位
            </div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-violet-900">
              {aiInterpretation.map((item) => (
                <p key={item}>• {item}</p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
              <Lightbulb className="h-4 w-4" />
              下一步建议
            </div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-amber-900">
              {nextActions.map((item) => (
                <p key={item}>• {item}</p>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">实验记录信息</h2>
            <div className="mt-4 space-y-4 text-sm">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">实验 ID</p>
                <p className="mt-1 break-all font-mono text-xs text-slate-800">{experiment.exp_id}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">方法数量</p>
                <p className="mt-1 text-slate-800">{experiment.steps.length} 个步骤</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">数据点</p>
                <p className="mt-1 text-slate-800">{experiment.data.length} 个</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
