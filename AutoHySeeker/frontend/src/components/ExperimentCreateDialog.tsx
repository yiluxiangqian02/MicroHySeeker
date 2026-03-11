import { useMemo, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  FlaskConical,
  Settings2,
  Sparkles,
  Target,
  X,
} from 'lucide-react';

interface ParamDef {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  defaultValue: number;
  hint?: string;
  advanced?: boolean;
}

interface StepTypeDef {
  label: string;
  summary: string;
  bestFor: string;
  params: ParamDef[];
  estimateSec: (params: Record<string, number>) => number;
}

const STEP_TYPES: Record<string, StepTypeDef> = {
  cv: {
    label: 'CV – 循环伏安法',
    summary: '适合做电极响应摸底、峰位观察和浓度差异筛查。',
    bestFor: '初步筛选 / 基线摸底 / 对照比较',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 0, hint: '建议覆盖目标氧化还原区间' },
      { key: 'endVoltage', label: '终止电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 1, hint: '与起始电压共同决定扫描窗口' },
      { key: 'scanRate', label: '扫描速率', unit: 'mV/s', min: 1, max: 10000, step: 1, defaultValue: 50, hint: '常用起步值 50 mV/s' },
      { key: 'cycles', label: '循环次数', unit: '次', min: 1, max: 100, step: 1, defaultValue: 1, hint: '首轮摸底建议先做 1–3 次' },
      { key: 'stepVoltage', label: '步进电压', unit: 'mV', min: 0.1, max: 100, step: 0.1, defaultValue: 5, advanced: true },
      { key: 'quietTime', label: '静置时间', unit: 's', min: 0, max: 3600, step: 1, defaultValue: 2, advanced: true },
      { key: 'sensitivity', label: '灵敏度', unit: 'μA', min: 1, max: 1000, step: 1, defaultValue: 100, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 1) - (p.startVoltage ?? 0)) * 1000;
      const rate = p.scanRate ?? 50;
      return Math.round((range / rate) * 2 * (p.cycles ?? 1) + (p.quietTime ?? 2));
    },
  },
  eis: {
    label: 'EIS – 电化学阻抗谱',
    summary: '适合评估界面传递、电荷转移和电极状态变化。',
    bestFor: '界面诊断 / 稳定性评估 / 故障复查',
    params: [
      { key: 'startFreq', label: '起始频率', unit: 'Hz', min: 0.01, max: 1e6, step: 1, defaultValue: 100000, hint: '通常从高频往低频扫' },
      { key: 'endFreq', label: '终止频率', unit: 'Hz', min: 0.01, max: 1e6, step: 0.01, defaultValue: 0.1, hint: '低频越低，测试越久' },
      { key: 'amplitude', label: '振幅', unit: 'mV', min: 1, max: 100, step: 1, defaultValue: 10, hint: '常见起步值 5–10 mV' },
      { key: 'dcVoltage', label: '直流偏压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 0 },
      { key: 'pointsPerDecade', label: '每十倍频点数', unit: '点', min: 5, max: 20, step: 1, defaultValue: 10, advanced: true },
      { key: 'integrationTime', label: '积分时间', unit: 's', min: 0.1, max: 10, step: 0.1, defaultValue: 1, advanced: true },
    ],
    estimateSec: (p) => {
      const decades = Math.log10((p.startFreq ?? 1e5) / Math.max(p.endFreq ?? 0.1, 0.001));
      const pts = decades * (p.pointsPerDecade ?? 10);
      return Math.round(pts * (p.integrationTime ?? 1) * 2);
    },
  },
  ca: {
    label: 'CA – 计时电流法',
    summary: '适合做时间响应、稳定性观察和台阶电位下的动态过程记录。',
    bestFor: '响应验证 / 时间曲线 / 稳定性测试',
    params: [
      { key: 'voltage', label: '施加电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 0.5, hint: '围绕目标反应电位设定' },
      { key: 'duration', label: '持续时间', unit: 's', min: 1, max: 36000, step: 1, defaultValue: 60, hint: '先用短时确认趋势，再扩时长' },
      { key: 'sampleInterval', label: '采样间隔', unit: 's', min: 0.01, max: 60, step: 0.01, defaultValue: 0.1, hint: '间隔越小，数据越细但文件更大' },
      { key: 'quietTime', label: '静置时间', unit: 's', min: 0, max: 3600, step: 1, defaultValue: 2, advanced: true },
      { key: 'sensitivity', label: '灵敏度', unit: 'μA', min: 1, max: 1000, step: 1, defaultValue: 100, advanced: true },
    ],
    estimateSec: (p) => (p.duration ?? 60) + (p.quietTime ?? 2),
  },
  cp: {
    label: 'CP – 计时电位法',
    summary: '适合恒流条件下观察电位演化和电极/体系变化。',
    bestFor: '恒流验证 / 耐久测试 / 条件评估',
    params: [
      { key: 'current', label: '施加电流', unit: 'mA', min: -1000, max: 1000, step: 0.1, defaultValue: 1, hint: '建议从较保守电流开始' },
      { key: 'duration', label: '持续时间', unit: 's', min: 1, max: 36000, step: 1, defaultValue: 60 },
      { key: 'sampleInterval', label: '采样间隔', unit: 's', min: 0.01, max: 60, step: 0.01, defaultValue: 0.1 },
      { key: 'quietTime', label: '静置时间', unit: 's', min: 0, max: 3600, step: 1, defaultValue: 2, advanced: true },
    ],
    estimateSec: (p) => (p.duration ?? 60) + (p.quietTime ?? 2),
  },
  lsv: {
    label: 'LSV – 线性扫描伏安法',
    summary: '适合做单向扫描、起始电位窗口探索和响应阈值判断。',
    bestFor: '单向扫描 / 阈值判断 / 方法预筛',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 0 },
      { key: 'endVoltage', label: '终止电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 1 },
      { key: 'scanRate', label: '扫描速率', unit: 'mV/s', min: 1, max: 10000, step: 1, defaultValue: 50 },
      { key: 'stepVoltage', label: '步进电压', unit: 'mV', min: 0.1, max: 100, step: 0.1, defaultValue: 5, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 1) - (p.startVoltage ?? 0)) * 1000;
      return Math.round(range / (p.scanRate ?? 50));
    },
  },
  dpv: {
    label: 'DPV – 差分脉冲伏安法',
    summary: '适合痕量分析和峰分辨要求更高的检测场景。',
    bestFor: '灵敏检测 / 峰分辨 / 定量分析',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: -0.5 },
      { key: 'endVoltage', label: '终止电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 0.5 },
      { key: 'pulseAmplitude', label: '脉冲幅度', unit: 'mV', min: 1, max: 250, step: 1, defaultValue: 50 },
      { key: 'pulseWidth', label: '脉冲宽度', unit: 'ms', min: 1, max: 1000, step: 1, defaultValue: 50, advanced: true },
      { key: 'scanRate', label: '扫描速率', unit: 'mV/s', min: 1, max: 1000, step: 1, defaultValue: 5, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 0.5) - (p.startVoltage ?? -0.5)) * 1000;
      return Math.round(range / (p.scanRate ?? 5));
    },
  },
  sqv: {
    label: 'SWV – 方波伏安法',
    summary: '适合快速扫描和高灵敏度筛查。',
    bestFor: '快速筛查 / 灵敏检测 / 条件比较',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: -0.5 },
      { key: 'endVoltage', label: '终止电压', unit: 'V', min: -10, max: 10, step: 0.1, defaultValue: 0.5 },
      { key: 'frequency', label: '频率', unit: 'Hz', min: 1, max: 1000, step: 1, defaultValue: 15 },
      { key: 'amplitude', label: '幅度', unit: 'mV', min: 1, max: 250, step: 1, defaultValue: 25, advanced: true },
      { key: 'increment', label: '电位增量', unit: 'mV', min: 0.1, max: 10, step: 0.1, defaultValue: 2, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 0.5) - (p.startVoltage ?? -0.5)) * 1000;
      const inc = p.increment ?? 2;
      return Math.round((range / inc) / (p.frequency ?? 15));
    },
  },
};

const RESEARCH_GOALS = [
  {
    id: 'screening',
    title: '筛选条件',
    subtitle: '先快速找到值得继续放大的参数区间。',
    suggestion: '建议先用 CV / SWV 做快速摸底。',
    recommendedMethods: ['cv', 'sqv', 'lsv'],
  },
  {
    id: 'calibration',
    title: '做标定',
    subtitle: '确认浓度、响应幅度或线性关系是否稳定。',
    suggestion: '优先选 CV / DPV，便于看峰电流和灵敏度。',
    recommendedMethods: ['cv', 'dpv', 'ca'],
  },
  {
    id: 'validation',
    title: '验证假设',
    subtitle: '针对既有判断做一轮有明确结论标准的实验。',
    suggestion: '可保守起步，优先减少变量数量。',
    recommendedMethods: ['cv', 'ca', 'cp'],
  },
  {
    id: 'reproduction',
    title: '复现结果',
    subtitle: '确认前次结果是否可重复，重点看一致性。',
    suggestion: '建议保留与历史实验一致的关键参数。',
    recommendedMethods: ['cv', 'ca', 'eis'],
  },
  {
    id: 'diagnosis',
    title: '故障复查',
    subtitle: '当结果异常、漂移明显或怀疑界面问题时使用。',
    suggestion: 'EIS + CV 是常见的排查组合。',
    recommendedMethods: ['eis', 'cv', 'ca'],
  },
];

const WIZARD_STEPS = [
  {
    key: 'goal',
    title: '明确目标',
    desc: '先说清这次实验想回答什么问题。',
    icon: Target,
  },
  {
    key: 'method',
    title: '选择方法',
    desc: '按科研目的挑选最合适的电化学方法。',
    icon: FlaskConical,
  },
  {
    key: 'params',
    title: '确认参数',
    desc: '先定必要参数，高级参数保留默认值也可以。',
    icon: Settings2,
  },
  {
    key: 'check',
    title: '执行前检查',
    desc: '确认时长、重点观察项和下一步动作。',
    icon: CheckCircle2,
  },
] as const;

interface StepState {
  step_type: string;
  description: string;
  params: Record<string, number>;
  showAdvanced: boolean;
}

interface ExperimentCreateDialogProps {
  onClose: () => void;
  onSubmit: (experiment: Record<string, unknown>) => void;
}

function buildDefaultParams(stepType: string): Record<string, number> {
  const def = STEP_TYPES[stepType];
  if (!def) return {};
  return Object.fromEntries(def.params.map((p) => [p.key, p.defaultValue]));
}

function formatDuration(sec: number): string {
  if (sec < 60) return `${sec} 秒`;
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${h} 小时 ${m} 分`;
  if (m > 0 && s > 0) return `${m} 分 ${s} 秒`;
  return `${m} 分钟`;
}

function formatParamValue(value: number, unit: string) {
  if (Number.isInteger(value)) return `${value} ${unit}`;
  return `${value.toFixed(2).replace(/\.00$/, '')} ${unit}`;
}

interface NumInputProps {
  def: ParamDef;
  value: number;
  onChange: (key: string, val: number) => void;
}

function NumInput({ def, value, onChange }: NumInputProps) {
  const [raw, setRaw] = useState(String(value));
  const [error, setError] = useState('');

  const handleBlur = () => {
    const n = parseFloat(raw);
    if (Number.isNaN(n)) {
      setError('请输入有效数字');
      setRaw(String(value));
      return;
    }
    if (n < def.min || n > def.max) {
      setError(`范围: ${def.min} ~ ${def.max}`);
      setRaw(String(value));
      return;
    }
    setError('');
    setRaw(String(n));
    onChange(def.key, n);
  };

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-gray-700">
        {def.label}
        {def.hint && <span className="ml-1 font-normal text-gray-400">({def.hint})</span>}
      </label>
      <div className={`flex overflow-hidden rounded-xl border ${error ? 'border-red-400' : 'border-gray-300'} bg-white focus-within:border-transparent focus-within:ring-2 focus-within:ring-blue-500`}>
        <input
          type="number"
          value={raw}
          min={def.min}
          max={def.max}
          step={def.step}
          onChange={(e) => setRaw(e.target.value)}
          onBlur={handleBlur}
          className="flex-1 px-3 py-2.5 text-sm focus:outline-none"
        />
        <span className="flex items-center border-l border-gray-300 bg-gray-50 px-3 text-xs text-gray-500">
          {def.unit}
        </span>
      </div>
      {error ? (
        <p className="mt-1 text-xs text-red-500">{error}</p>
      ) : (
        <p className="mt-1 text-xs text-gray-400">范围: {def.min} ~ {def.max} {def.unit}</p>
      )}
    </div>
  );
}

export function ExperimentCreateDialog({ onClose, onSubmit }: ExperimentCreateDialogProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [goal, setGoal] = useState(RESEARCH_GOALS[0].id);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [selectedMethod, setSelectedMethod] = useState('cv');
  const [stepDescription, setStepDescription] = useState('');
  const [params, setParams] = useState<Record<string, number>>(buildDefaultParams('cv'));
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const goalDef = RESEARCH_GOALS.find((item) => item.id === goal) ?? RESEARCH_GOALS[0];
  const methodDef = STEP_TYPES[selectedMethod];
  const estimatedSec = methodDef?.estimateSec(params) ?? 0;
  const basicParams = methodDef?.params.filter((p) => !p.advanced) ?? [];
  const advancedParams = methodDef?.params.filter((p) => p.advanced) ?? [];

  const recommendedMethodSet = new Set(goalDef.recommendedMethods);

  const summaryItems = useMemo(
    () => basicParams.slice(0, 4).map((item) => ({
      label: item.label,
      value: formatParamValue(params[item.key] ?? item.defaultValue, item.unit),
    })),
    [basicParams, params],
  );

  const previewExperiment = useMemo(
    () => ({
      name: name.trim() || `${goalDef.title} · ${methodDef.label}`,
      description: description.trim() || `${goalDef.subtitle} ${goalDef.suggestion}`,
      steps: [
        {
          step_type: selectedMethod,
          description: stepDescription.trim() || `${goalDef.title}：${methodDef.bestFor}`,
          params,
        },
      ],
    }),
    [name, goalDef, methodDef, description, selectedMethod, stepDescription, params],
  );

  const applyMethod = (methodKey: string) => {
    setSelectedMethod(methodKey);
    setParams(buildDefaultParams(methodKey));
    setShowAdvanced(false);
  };

  const updateParam = (key: string, val: number) => {
    setParams((prev) => ({ ...prev, [key]: val }));
  };

  const nextStep = () => {
    if (currentStep === 0 && !name.trim()) {
      setError('请先给这次实验起一个便于回看的名字。');
      return;
    }
    setError('');
    setCurrentStep((prev) => Math.min(prev + 1, WIZARD_STEPS.length - 1));
  };

  const prevStep = () => {
    setError('');
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  };

  const handleSubmit = async () => {
    if (!name.trim()) {
      setCurrentStep(0);
      setError('请输入实验名称');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const payload = {
        name: previewExperiment.name,
        description: previewExperiment.description,
        steps: previewExperiment.steps.map((step) => ({
          step_type: step.step_type,
          description: step.description,
          params: Object.fromEntries(Object.entries(step.params).map(([k, v]) => [k, String(v)])),
        })),
        tags: [goalDef.title, methodDef.label.split(' – ')[0], ...tags.split(',').map((t) => t.trim()).filter(Boolean)],
      };

      const response = await fetch('/api/experiments/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || '创建失败');
      }

      const experiment = await response.json();
      onSubmit(experiment);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '网络错误，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="border-b border-slate-200 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-blue-600">实验向导</p>
              <h3 className="mt-1 text-2xl font-bold text-slate-900">把这次实验组织成一个清晰的科研任务</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                先确定目的，再选方法，再确认关键参数。你会始终知道自己现在在哪一步、接下来该做什么。
              </p>
            </div>
            <button onClick={onClose} className="rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-4">
            {WIZARD_STEPS.map((step, index) => {
              const Icon = step.icon;
              const active = index === currentStep;
              const done = index < currentStep;
              return (
                <div
                  key={step.key}
                  className={`rounded-xl border p-4 ${active ? 'border-blue-500 bg-blue-50' : done ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-slate-50'}`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-full ${active ? 'bg-blue-600 text-white' : done ? 'bg-emerald-600 text-white' : 'bg-white text-slate-500 border border-slate-200'}`}>
                      {done ? <CheckCircle2 className="h-5 w-5" /> : <Icon className="h-4 w-4" />}
                    </div>
                    <div>
                      <p className="text-xs font-medium text-slate-500">Step {index + 1}</p>
                      <p className="text-sm font-semibold text-slate-900">{step.title}</p>
                    </div>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-slate-600">{step.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[1.45fr,0.9fr]">
          <div className="space-y-6">
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            {currentStep === 0 && (
              <section className="space-y-5">
                <div>
                  <h4 className="text-lg font-semibold text-slate-900">这次实验想解决什么问题？</h4>
                  <p className="mt-1 text-sm text-slate-600">先把科研意图讲清楚，后面的参数选择才不会变成盲填。</p>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">实验名称</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例如：Fe3+ 浓度梯度首轮 CV 摸底"
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">实验目标</label>
                  <div className="grid gap-3 md:grid-cols-2">
                    {RESEARCH_GOALS.map((item) => {
                      const selected = item.id === goal;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => setGoal(item.id)}
                          className={`rounded-xl border p-4 text-left transition ${selected ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50'}`}
                        >
                          <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                          <p className="mt-1 text-sm text-slate-600">{item.subtitle}</p>
                          <p className="mt-3 text-xs text-blue-700">{item.suggestion}</p>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">补充说明（可选）</label>
                  <textarea
                    rows={4}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="例如：先看 0.1–0.5 mM 是否能稳定拉开峰电流差异，如果有趋势，再扩展到更低浓度。"
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </section>
            )}

            {currentStep === 1 && (
              <section className="space-y-5">
                <div>
                  <h4 className="text-lg font-semibold text-slate-900">用什么方法最合适？</h4>
                  <p className="mt-1 text-sm text-slate-600">系统会优先突出与当前目标更匹配的方法，但你仍可自由切换。</p>
                </div>

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-semibold">当前目标：{goalDef.title}</p>
                  <p className="mt-1">{goalDef.suggestion}</p>
                </div>

                <div className="grid gap-3">
                  {Object.entries(STEP_TYPES).map(([key, def]) => {
                    const selected = key === selectedMethod;
                    const recommended = recommendedMethodSet.has(key);
                    return (
                      <button
                        key={key}
                        type="button"
                        onClick={() => applyMethod(key)}
                        className={`rounded-xl border p-4 text-left transition ${selected ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-slate-200 bg-white hover:border-blue-300'} `}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-base font-semibold text-slate-900">{def.label}</p>
                          {recommended && (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                              适合当前目标
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-sm text-slate-600">{def.summary}</p>
                        <p className="mt-2 text-xs text-slate-500">更适合：{def.bestFor}</p>
                      </button>
                    );
                  })}
                </div>
              </section>
            )}

            {currentStep === 2 && (
              <section className="space-y-5">
                <div>
                  <h4 className="text-lg font-semibold text-slate-900">先把关键参数定下来</h4>
                  <p className="mt-1 text-sm text-slate-600">
                    当前方法为 <span className="font-medium text-slate-900">{methodDef.label}</span>。先填必要参数，高级参数不确定时保留默认值即可。
                  </p>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">这一步的备注（可选）</label>
                  <input
                    type="text"
                    value={stepDescription}
                    onChange={(e) => setStepDescription(e.target.value)}
                    placeholder="例如：先做 50 mV/s 的首轮摸底，确认是否出现可分辨峰位"
                    className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  {basicParams.map((param) => (
                    <NumInput
                      key={param.key}
                      def={param}
                      value={params[param.key] ?? param.defaultValue}
                      onChange={updateParam}
                    />
                  ))}
                </div>

                {advancedParams.length > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <button
                      type="button"
                      onClick={() => setShowAdvanced((prev) => !prev)}
                      className="flex items-center gap-2 text-sm font-medium text-slate-700"
                    >
                      {showAdvanced ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      高级参数（需要时再展开）
                    </button>
                    {showAdvanced && (
                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        {advancedParams.map((param) => (
                          <NumInput
                            key={param.key}
                            def={param}
                            value={params[param.key] ?? param.defaultValue}
                            onChange={updateParam}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}

            {currentStep === 3 && (
              <section className="space-y-5">
                <div>
                  <h4 className="text-lg font-semibold text-slate-900">执行前检查</h4>
                  <p className="mt-1 text-sm text-slate-600">最后快速确认：这轮实验为什么做、怎么做、做完后先看什么。</p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="grid gap-5 md:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">实验目标</p>
                      <p className="mt-2 text-base font-semibold text-slate-900">{goalDef.title}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{previewExperiment.description}</p>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">本次方法</p>
                      <p className="mt-2 text-base font-semibold text-slate-900">{methodDef.label}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{methodDef.summary}</p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-blue-900">
                      <Clock className="h-4 w-4" />
                      预计时长
                    </div>
                    <p className="mt-3 text-2xl font-bold text-blue-900">{formatDuration(estimatedSec)}</p>
                    <p className="mt-1 text-xs text-blue-700">首轮建议保持单步短实验，先确认趋势再扩展。</p>
                  </div>
                  <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-emerald-900">
                      <Sparkles className="h-4 w-4" />
                      重点观察
                    </div>
                    <ul className="mt-3 space-y-1 text-sm text-emerald-800">
                      <li>• 曲线形态是否符合预期</li>
                      <li>• 关键响应是否足够稳定</li>
                      <li>• 是否需要补对照/重复组</li>
                    </ul>
                  </div>
                  <div className="rounded-xl border border-amber-100 bg-amber-50 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
                      <Target className="h-4 w-4" />
                      做完下一步
                    </div>
                    <ul className="mt-3 space-y-1 text-sm text-amber-800">
                      <li>• 查看结果摘要</li>
                      <li>• 请求 AI 初步解读</li>
                      <li>• 决定是否扩参数或复现</li>
                    </ul>
                  </div>
                </div>
              </section>
            )}
          </div>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-900 p-5 text-white shadow-sm">
              <p className="text-sm font-medium text-blue-200">实验草案</p>
              <h4 className="mt-2 text-xl font-semibold">{previewExperiment.name}</h4>
              <p className="mt-3 text-sm leading-6 text-slate-200">{previewExperiment.description}</p>

              <div className="mt-5 space-y-3 border-t border-white/10 pt-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">目标</p>
                  <p className="mt-1 text-sm text-white">{goalDef.title}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">方法</p>
                  <p className="mt-1 text-sm text-white">{methodDef.label}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">预计时长</p>
                  <p className="mt-1 text-sm text-white">{formatDuration(estimatedSec)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-400">步骤备注</p>
                  <p className="mt-1 text-sm text-white/90">{stepDescription.trim() || '暂无，后续会按默认建议执行。'}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h4 className="text-base font-semibold text-slate-900">关键参数摘要</h4>
              <div className="mt-4 space-y-3">
                {summaryItems.map((item) => (
                  <div key={item.label} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                    <span className="text-sm text-slate-600">{item.label}</span>
                    <span className="text-sm font-medium text-slate-900">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h4 className="text-base font-semibold text-slate-900">标签（可选）</h4>
              <p className="mt-1 text-sm text-slate-600">便于后续回看、对比和筛选。</p>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="例如：Fe3+, 基线, 首轮摸底"
                className="mt-3 w-full rounded-xl border border-gray-300 px-4 py-3 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </aside>
        </div>

        <div className="flex flex-col gap-3 border-t border-slate-200 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-500">
            当前处于 <span className="font-medium text-slate-700">Step {currentStep + 1}</span>：{WIZARD_STEPS[currentStep].title}
          </div>
          <div className="flex gap-3">
            <button
              onClick={currentStep === 0 ? onClose : prevStep}
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ArrowLeft className="h-4 w-4" />
              {currentStep === 0 ? '取消' : '上一步'}
            </button>

            {currentStep < WIZARD_STEPS.length - 1 ? (
              <button
                onClick={nextStep}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700"
              >
                下一步
                <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-400"
              >
                <CheckCircle2 className="h-4 w-4" />
                {submitting ? '创建中...' : '创建实验并进入详情'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
