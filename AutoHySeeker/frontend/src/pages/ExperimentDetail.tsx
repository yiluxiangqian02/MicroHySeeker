import { useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  ChevronRight,
  Clock,
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

const STATUS_CONFIG: Record<string, { icon: ReactNode; label: string; color: string; summary: string }> = {
  created: {
    icon: <Clock className="h-5 w-5" />,
    label: '待执行',
    color: 'text-slate-700 bg-slate-100',
    summary: '实验方案已准备好，下一步可以直接启动执行。',
  },
  running: {
    icon: <Play className="h-5 w-5 animate-pulse" />,
    label: '运行中',
    color: 'text-blue-700 bg-blue-100',
    summary: '实验正在执行，当前重点是盯住进度、曲线和异常信号。',
  },
  completed: {
    icon: <CheckCircle className="h-5 w-5" />,
    label: '已完成',
    color: 'text-emerald-700 bg-emerald-100',
    summary: '实验已结束，可以进入结果回看、AI 解读和下一步决策。',
  },
  failed: {
    icon: <AlertCircle className="h-5 w-5" />,
    label: '执行异常',
    color: 'text-red-700 bg-red-100',
    summary: '实验未顺利完成，建议优先回看参数设置、设备状态和最近异常。',
  },
};

const STEP_LABELS: Record<string, string> = {
  cv: 'CV · 循环伏安法',
  eis: 'EIS · 电化学阻抗谱',
  ca: 'CA · 计时电流法',
  cp: 'CP · 计时电位法',
  lsv: 'LSV · 线性扫描伏安法',
  dpv: 'DPV · 差分脉冲伏安法',
  sqv: 'SWV · 方波伏安法',
};

function formatDateTime(value?: string) {
  if (!value) return '—';
  return new Date(value).toLocaleString('zh-CN');
}

function formatParamValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function humanizeParamKey(key: string) {
  const labels: Record<string, string> = {
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
  return labels[key] ?? key;
}

function deriveGoal(experiment: Experiment) {
  const text = `${experiment.name} ${experiment.description} ${experiment.tags.join(' ')}`.toLowerCase();
  if (text.includes('标定') || text.includes('calibration')) return '本次目标偏向标定或定量判断';
  if (text.includes('复现') || text.includes('repro')) return '本次目标偏向复现已有结果';
  if (text.includes('故障') || text.includes('异常') || text.includes('diagnosis')) return '本次目标偏向故障复查与原因定位';
  if (text.includes('验证') || text.includes('validate')) return '本次目标偏向验证已有假设';
  return '本次目标偏向首轮探索或条件筛选';
}

function deriveResultSummary(experiment: Experiment) {
  if (experiment.status === 'created') return '实验尚未开始，当前还没有结果数据。';
  if (experiment.status === 'running') {
    return experiment.data.length > 0
      ? `已采集 ${experiment.data.length} 个数据点，可先看曲线是否出现预期趋势。`
      : '实验正在执行，结果会随着采集逐步形成。';
  }
  if (experiment.status === 'failed') {
    return '本轮实验未顺利完成，优先检查参数窗口、设备连接和样品状态。';
  }
  if (experiment.data.length === 0) return '实验已完成，但当前还没有可展示的数据点。';
  return `本轮实验已得到 ${experiment.data.length} 个数据点，可继续做峰位、趋势或稳定性判断。`;
}

function deriveAiInterpretation(experiment: Experiment) {
  if (experiment.status === 'created') {
    return 'AI 解读将在实验开始后出现。当前更重要的是确认实验目标和关键参数是否合理。';
  }
  if (experiment.status === 'running') {
    return 'AI 解读占位：后续这里会给出运行中趋势识别、异常提示和是否建议提前终止/扩展条件。';
  }
  if (experiment.status === 'failed') {
    return 'AI 解读占位：后续这里会给出最可能失败原因、排查顺序，以及推荐补做的诊断实验。';
  }
  return 'AI 解读占位：后续这里会自动生成结果摘要、关键趋势判断，以及与历史实验的对比结论。';
}

function deriveNextActions(experiment: Experiment) {
  if (experiment.status === 'created') {
    return [
      '确认实验窗口是否覆盖目标响应区间，然后启动执行。',
      '如果这是首轮摸底，优先保持单变量、短时长，先拿到第一版曲线。',
      '准备好对照组或重复组，便于后续判断结果是否稳定。',
    ];
  }
  if (experiment.status === 'running') {
    return [
      '持续观察曲线是否出现明显漂移、突变或平台段异常。',
      '如已出现可疑趋势，记录时间点，方便实验后回看。',
      '完成后优先看关键响应是否值得做复现或扩参数。',
    ];
  }
  if (experiment.status === 'failed') {
    return [
      '先回看关键参数和设备连接，再判断是否需要缩小参数窗口重跑。',
      '建议补做一个更保守的对照实验，排除样品或装置问题。',
      '如异常持续出现，优先切到 EIS / CV 组合做诊断。',
    ];
  }
  return [
    '先确认曲线是否支持原始实验目标，再决定要不要扩展参数范围。',
    '如果结果可用，优先补重复组或对照组，增强结论可信度。',
    '把这轮结果交给 AI 助手做进一步解读和下一轮建议。',
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
      alert('实验已开始执行，接下来可以重点关注状态和数据变化。');
    } catch (err) {
      alert(err instanceof Error ? err.message : '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  const summaryParams = useMemo(() => {
    const firstStep = experiment?.steps?.[0];
    if (!firstStep?.params) return [];
    return Object.entries(firstStep.params).slice(0, 6);
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
  const goalSummary = deriveGoal(experiment);
  const resultSummary = deriveResultSummary(experiment);
  const aiInterpretation = deriveAiInterpretation(experiment);
  const nextActions = deriveNextActions(experiment);
  const firstStep = experiment.steps[0];

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
          <p className="text-sm font-medium text-blue-600">实验闭环页</p>
          <h2 className="mt-1 text-3xl font-bold text-slate-900">{experiment.name}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            {experiment.description || '当前未填写实验说明。建议后续补充实验目的，便于结果回看和 AI 解读。'}
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${statusConf.color}`}>
              {statusConf.icon}
              {statusConf.label}
            </span>
            {experiment.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-blue-50 px-2.5 py-1 text-xs text-blue-700">
                {tag}
              </span>
            ))}
          </div>
        </div>

        {experiment.status === 'created' && (
          <button
            onClick={handleExecute}
            disabled={executing}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 font-medium text-white transition hover:bg-blue-700 disabled:bg-blue-400"
          >
            <Play className="h-4 w-4" />
            {executing ? '提交中...' : '开始执行这轮实验'}
          </button>
        )}
      </div>

      <section className="grid gap-4 xl:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm xl:col-span-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Target className="h-4 w-4 text-blue-600" />
            实验目标
          </div>
          <p className="mt-3 text-base font-semibold text-slate-900">{goalSummary}</p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{statusConf.summary}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Clock className="h-4 w-4 text-blue-600" />
            执行状态
          </div>
          <div className={`mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${statusConf.color}`}>
            {statusConf.icon}
            {statusConf.label}
          </div>
          <div className="mt-4 space-y-2 text-sm text-slate-600">
            <p>创建时间：{formatDateTime(experiment.created_at)}</p>
            <p>开始时间：{formatDateTime(experiment.started_at)}</p>
            <p>结束时间：{formatDateTime(experiment.completed_at)}</p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <FlaskConical className="h-4 w-4 text-blue-600" />
            方案摘要
          </div>
          <p className="mt-3 text-sm font-medium text-slate-900">
            {firstStep ? STEP_LABELS[firstStep.step_type] ?? firstStep.step_type.toUpperCase() : '暂无步骤'}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            {firstStep?.description || '当前未填写步骤备注。'}
          </p>
          <p className="mt-3 text-xs text-slate-500">共 {experiment.steps.length} 个实验步骤</p>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-slate-900">关键参数摘要</h3>
              <span className="text-xs text-slate-400">优先展示最影响实验结论的参数</span>
            </div>
            {summaryParams.length > 0 ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {summaryParams.map(([key, value]) => (
                  <div key={key} className="rounded-xl bg-slate-50 px-4 py-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{humanizeParamKey(key)}</p>
                    <p className="mt-2 text-base font-semibold text-slate-900">{formatParamValue(value)}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-xl border-2 border-dashed border-slate-200 p-6 text-sm text-slate-500">
                暂无可展示的参数摘要。
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">实验步骤</h3>
            <div className="mt-4 space-y-3">
              {experiment.steps.map((step, index) => (
                <div key={`${step.step_type}-${index}`} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-start gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                      {index + 1}
                    </span>
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                          {STEP_LABELS[step.step_type] ?? step.step_type.toUpperCase()}
                        </span>
                        <span className="text-sm text-slate-700">{step.description || `步骤 ${index + 1}`}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {Object.entries(step.params).slice(0, 5).map(([key, value]) => (
                          <span key={key} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
                            {humanizeParamKey(key)}: {formatParamValue(value)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">结果占位</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{resultSummary}</p>

            <div className="mt-5 rounded-xl border border-slate-200 p-4">
              <h4 className="text-sm font-semibold text-slate-900">实验数据</h4>
              {experiment.data.length > 0 ? (
                <div className="mt-4 h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={experiment.data}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="x" label={{ value: 'E / V', position: 'insideBottomRight', offset: -5 }} />
                      <YAxis label={{ value: 'I / A', angle: -90, position: 'insideLeft' }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="y" stroke="#2563EB" dot={false} strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="mt-4 flex h-36 items-center justify-center rounded-xl border-2 border-dashed border-slate-200 text-sm text-slate-400">
                  暂无实验数据{experiment.status === 'created' ? '，请先启动执行。' : '，后续会在这里展示曲线与摘要。'}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-6 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-900">
              <Sparkles className="h-4 w-4" />
              AI 解读占位
            </div>
            <p className="mt-3 text-sm leading-6 text-blue-900/90">{aiInterpretation}</p>
            <div className="mt-4 rounded-xl bg-white/70 p-4 text-sm text-blue-800">
              计划中的输出包括：结果摘要、异常点提示、与历史实验对比、以及下一轮参数建议。
            </div>
          </div>

          <div className="rounded-2xl border border-amber-100 bg-amber-50 p-6 shadow-sm">
            <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
              <Lightbulb className="h-4 w-4" />
              下一步建议
            </div>
            <div className="mt-4 space-y-3">
              {nextActions.map((item, index) => (
                <div key={index} className="flex items-start gap-3 rounded-xl bg-white/70 p-3 text-sm text-amber-900">
                  <ChevronRight className="mt-0.5 h-4 w-4 flex-shrink-0" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-base font-semibold text-slate-900">实验信息</h3>
            <div className="mt-4 space-y-3 text-sm text-slate-600">
              <div className="flex items-start justify-between gap-4">
                <span>实验 ID</span>
                <span className="font-mono text-xs text-slate-900">{experiment.exp_id}</span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>标签数</span>
                <span className="text-slate-900">{experiment.tags.length}</span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>数据点数</span>
                <span className="text-slate-900">{experiment.data.length}</span>
              </div>
              <div className="flex items-start justify-between gap-4">
                <span>当前阶段</span>
                <span className="text-slate-900">{statusConf.label}</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
