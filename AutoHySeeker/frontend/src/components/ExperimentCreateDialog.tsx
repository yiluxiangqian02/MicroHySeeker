import { useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Beaker,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Droplets,
  FlaskConical,
  Plus,
  Trash2,
  Wind,
  X,
} from 'lucide-react';

type StepType = 'prep_sol' | 'transfer' | 'flush' | 'echem' | 'blank' | 'evacuate';
type EchemTechnique = 'CV' | 'LSV' | 'i-t' | 'EIS' | 'ADT';

type ExperimentStep = {
  step_id: string;
  step_type: StepType;
  notes: string;
  pump_address?: number;
  pump_direction?: 'FWD' | 'REV';
  pump_rpm?: number;
  volume_ul?: number;
  transfer_duration?: number;
  transfer_duration_unit?: 'ms' | 's' | 'min' | 'hr' | 'cycle';
  flush_channel_id?: string;
  flush_rpm?: number;
  flush_cycle_duration_s?: number;
  flush_cycles?: number;
  prep_sol_params?: {
    total_volume_ul: number;
    selected_solutions: Record<string, boolean>;
    target_concentrations: Record<string, number>;
    solvent_flags: Record<string, boolean>;
    injection_order_numbers: Record<string, number>;
    injection_order: string[];
  };
  ec_settings?: {
    technique: EchemTechnique;
    e0?: number;
    eh?: number;
    el?: number;
    ef?: number;
    scan_rate?: number;
    sample_interval_ms?: number;
    quiet_time_s?: number;
    seg_num?: number;
    run_time_s?: number;
    freq_low?: number;
    freq_high?: number;
    amplitude?: number;
    adt_num_cycles?: number;
  };
};

interface ExperimentCreateDialogProps {
  onClose: () => void;
  onSubmit: (experiment: Record<string, unknown>) => void;
}

const STEP_META: Record<StepType, { label: string; description: string; icon: typeof FlaskConical; tone: string }> = {
  prep_sol: {
    label: 'prep_sol · 配液/混液',
    description: '为实验准备溶液配比、浓度和注液顺序。',
    icon: Beaker,
    tone: 'bg-violet-50 text-violet-700 border-violet-200',
  },
  transfer: {
    label: 'transfer · 移液/转移',
    description: '按体积或按时长驱动泵完成转移。',
    icon: ArrowUp,
    tone: 'bg-sky-50 text-sky-700 border-sky-200',
  },
  flush: {
    label: 'flush · 冲洗',
    description: '围绕 flush channel 做循环冲洗。',
    icon: Droplets,
    tone: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  },
  echem: {
    label: 'echem · 电化学测试',
    description: 'Technique 只是 echem 步骤内部的一个字段。',
    icon: FlaskConical,
    tone: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  blank: {
    label: 'blank · 空白/等待',
    description: '用于人工观察、占位、流程分段。',
    icon: ChevronRight,
    tone: 'bg-slate-50 text-slate-700 border-slate-200',
  },
  evacuate: {
    label: 'evacuate · 排空',
    description: '独立表达排空动作，不和 flush/transfer 混写。',
    icon: Wind,
    tone: 'bg-amber-50 text-amber-700 border-amber-200',
  },
};

const DEFAULT_SOLUTIONS = ['Buffer', 'Analyte', 'Mediator', 'Solvent A'];
const TECHNIQUE_FIELDS: Record<EchemTechnique, Array<{ key: string; label: string; unit?: string }>> = {
  CV: [
    { key: 'e0', label: '起始电位', unit: 'V' },
    { key: 'eh', label: '高电位', unit: 'V' },
    { key: 'el', label: '低电位', unit: 'V' },
    { key: 'ef', label: '最终电位', unit: 'V' },
    { key: 'scan_rate', label: '扫描速率', unit: 'V/s' },
    { key: 'seg_num', label: '循环段数' },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  ],
  LSV: [
    { key: 'e0', label: '起始电位', unit: 'V' },
    { key: 'ef', label: '最终电位', unit: 'V' },
    { key: 'scan_rate', label: '扫描速率', unit: 'V/s' },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  ],
  'i-t': [
    { key: 'e0', label: '施加电位', unit: 'V' },
    { key: 'run_time_s', label: '持续时间', unit: 's' },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  ],
  EIS: [
    { key: 'freq_high', label: '最高频率', unit: 'Hz' },
    { key: 'freq_low', label: '最低频率', unit: 'Hz' },
    { key: 'amplitude', label: '交流振幅', unit: 'V' },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  ],
  ADT: [
    { key: 'adt_num_cycles', label: 'ADT 循环数' },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  ],
};

function createStep(type: StepType = 'prep_sol', index = 0): ExperimentStep {
  return {
    step_id: `step_${Date.now()}_${index}`,
    step_type: type,
    notes: '',
    pump_address: 1,
    pump_direction: 'FWD',
    pump_rpm: 120,
    volume_ul: 1000,
    transfer_duration: 30,
    transfer_duration_unit: 's',
    flush_channel_id: 'flush-1',
    flush_rpm: 100,
    flush_cycle_duration_s: 30,
    flush_cycles: 1,
    prep_sol_params: {
      total_volume_ul: 100000,
      selected_solutions: Object.fromEntries(DEFAULT_SOLUTIONS.map((name, idx) => [name, idx < 2])),
      target_concentrations: Object.fromEntries(DEFAULT_SOLUTIONS.map((name, idx) => [name, idx === 0 ? 0 : 0.1])),
      solvent_flags: Object.fromEntries(DEFAULT_SOLUTIONS.map((name, idx) => [name, idx === DEFAULT_SOLUTIONS.length - 1])),
      injection_order_numbers: Object.fromEntries(DEFAULT_SOLUTIONS.map((name, idx) => [name, idx + 1])),
      injection_order: DEFAULT_SOLUTIONS,
    },
    ec_settings: {
      technique: 'CV',
      e0: 0,
      eh: 0.8,
      el: -0.2,
      ef: 0,
      scan_rate: 0.05,
      sample_interval_ms: 100,
      quiet_time_s: 2,
      seg_num: 2,
      run_time_s: 60,
      freq_low: 1,
      freq_high: 100000,
      amplitude: 0.005,
      adt_num_cycles: 100,
    },
  };
}

function formatStepSummary(step: ExperimentStep) {
  switch (step.step_type) {
    case 'prep_sol': {
      const prep = step.prep_sol_params;
      const selected = Object.entries(prep?.selected_solutions ?? {})
        .filter(([, enabled]) => enabled)
        .map(([name]) => name);
      return `${((prep?.total_volume_ul ?? 0) / 1000).toFixed(1)} mL · ${selected.length > 0 ? selected.join(' / ') : '未选溶液'}`;
    }
    case 'transfer':
      return step.volume_ul ? `${step.volume_ul} μL · 泵 ${step.pump_address}` : `${step.transfer_duration ?? 0} ${step.transfer_duration_unit ?? 's'} · 泵 ${step.pump_address}`;
    case 'flush':
      return `${step.flush_channel_id ?? '未选通道'} · ${step.flush_cycles ?? 1} cycles`;
    case 'echem':
      return `${step.ec_settings?.technique ?? 'CV'} · sample ${step.ec_settings?.sample_interval_ms ?? 100} ms`;
    case 'blank':
      return step.notes || '空白/等待占位';
    case 'evacuate':
      return `${step.volume_ul ? `${step.volume_ul} μL` : `${step.transfer_duration ?? 0} ${step.transfer_duration_unit ?? 's'}`} · 排空`;
    default:
      return '未配置';
  }
}

function NumberField({
  label,
  value,
  unit,
  onChange,
  min,
}: {
  label: string;
  value?: number;
  unit?: string;
  onChange: (value: number) => void;
  min?: number;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">{label}</span>
      <div className="flex overflow-hidden rounded-xl border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-blue-500">
        <input
          type="number"
          value={value ?? ''}
          min={min}
          onChange={(e) => onChange(Number(e.target.value))}
          className="flex-1 px-3 py-2.5 text-sm focus:outline-none"
        />
        {unit && <span className="flex items-center border-l border-slate-200 bg-slate-50 px-3 text-xs text-slate-500">{unit}</span>}
      </div>
    </label>
  );
}

export function ExperimentCreateDialog({ onClose, onSubmit }: ExperimentCreateDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [operator, setOperator] = useState('');
  const [tags, setTags] = useState('');
  const [steps, setSteps] = useState<ExperimentStep[]>([createStep('prep_sol', 0), createStep('echem', 1)]);
  const [expandedStepId, setExpandedStepId] = useState<string | null>(steps[0].step_id);
  const [showJsonPreview, setShowJsonPreview] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const activeIndex = Math.max(0, steps.findIndex((step) => step.step_id === expandedStepId));
  const activeStep = steps[activeIndex] ?? null;

  const updateStep = (stepId: string, updater: (step: ExperimentStep) => ExperimentStep) => {
    setSteps((prev) => prev.map((step) => (step.step_id === stepId ? updater(step) : step)));
  };

  const addStep = (type: StepType = 'blank') => {
    const next = createStep(type, steps.length);
    setSteps((prev) => [...prev, next]);
    setExpandedStepId(next.step_id);
  };

  const removeStep = (stepId: string) => {
    const next = steps.filter((step) => step.step_id !== stepId);
    setSteps(next);
    setExpandedStepId(next[0]?.step_id ?? null);
  };

  const moveStep = (index: number, dir: -1 | 1) => {
    const target = index + dir;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    setSteps(next);
  };

  const duplicateStep = (index: number) => {
    const clone = { ...steps[index], step_id: `step_${Date.now()}_${index}_copy` };
    const next = [...steps];
    next.splice(index + 1, 0, clone);
    setSteps(next);
    setExpandedStepId(clone.step_id);
  };

  const experimentDraft = useMemo(() => {
    const cleanSteps = steps.map((step) => ({
      ...step,
      notes: step.notes?.trim() ?? '',
    }));

    return {
      exp_name: name.trim() || '未命名实验',
      description: description.trim(),
      operator: operator.trim(),
      tags: tags.split(',').map((item) => item.trim()).filter(Boolean),
      steps: cleanSteps,
      notes: '',
    };
  }, [description, name, operator, steps, tags]);

  const riskHints = useMemo(() => {
    const hints: string[] = [];
    if (!steps.length) hints.push('当前没有任何步骤，无法执行。');
    if (!steps.some((step) => step.step_type === 'echem')) hints.push('当前方案没有 echem 步骤，无法产出电化学数据。');
    if (steps.some((step) => step.step_type === 'transfer' && !step.volume_ul && !step.transfer_duration)) {
      hints.push('存在 transfer 步骤但未设置体积或持续时间。');
    }
    if (steps.some((step) => step.step_type === 'prep_sol' && !Object.values(step.prep_sol_params?.selected_solutions ?? {}).some(Boolean))) {
      hints.push('存在 prep_sol 步骤但没有选中任何溶液。');
    }
    return hints;
  }, [steps]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('请先填写实验名称。');
      return;
    }
    if (!steps.length) {
      setError('请至少添加一个步骤。');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const payload = {
        name: experimentDraft.exp_name,
        description: experimentDraft.description,
        tags: [operator.trim() && `operator:${operator.trim()}`, ...experimentDraft.tags].filter(Boolean),
        steps: experimentDraft.steps.map((step) => ({
          step_type: step.step_type,
          description: step.notes || formatStepSummary(step),
          params: step,
        })),
      };

      const response = await fetch('/api/experiments/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const experiment = await response.json();
      onSubmit(experiment);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  const renderStepForm = (step: ExperimentStep) => {
    if (step.step_type === 'prep_sol') {
      const prep = step.prep_sol_params!;
      return (
        <div className="space-y-4">
          <NumberField
            label="总体积"
            value={prep.total_volume_ul}
            unit="μL"
            min={0}
            onChange={(value) => updateStep(step.step_id, (current) => ({
              ...current,
              prep_sol_params: { ...prep, total_volume_ul: value },
            }))}
          />
          <div className="rounded-2xl border border-slate-200">
            <div className="grid grid-cols-[1.2fr,0.8fr,0.6fr,0.6fr] gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold text-slate-500">
              <span>溶液</span>
              <span>目标浓度 (mol/L)</span>
              <span>溶剂</span>
              <span>注液顺序</span>
            </div>
            <div className="divide-y divide-slate-100">
              {prep.injection_order.map((solution) => (
                <div key={solution} className="grid grid-cols-[1.2fr,0.8fr,0.6fr,0.6fr] gap-3 px-4 py-3 text-sm text-slate-700">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={prep.selected_solutions[solution] ?? false}
                      onChange={(e) => updateStep(step.step_id, (current) => ({
                        ...current,
                        prep_sol_params: {
                          ...prep,
                          selected_solutions: { ...prep.selected_solutions, [solution]: e.target.checked },
                        },
                      }))}
                    />
                    <span>{solution}</span>
                  </label>
                  <input
                    type="number"
                    value={prep.target_concentrations[solution] ?? 0}
                    onChange={(e) => updateStep(step.step_id, (current) => ({
                      ...current,
                      prep_sol_params: {
                        ...prep,
                        target_concentrations: { ...prep.target_concentrations, [solution]: Number(e.target.value) },
                      },
                    }))}
                    className="rounded-lg border border-slate-300 px-3 py-2"
                  />
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={prep.solvent_flags[solution] ?? false}
                      onChange={(e) => updateStep(step.step_id, (current) => ({
                        ...current,
                        prep_sol_params: {
                          ...prep,
                          solvent_flags: { ...prep.solvent_flags, [solution]: e.target.checked },
                        },
                      }))}
                    />
                    <span>是</span>
                  </label>
                  <input
                    type="number"
                    value={prep.injection_order_numbers[solution] ?? 1}
                    onChange={(e) => updateStep(step.step_id, (current) => ({
                      ...current,
                      prep_sol_params: {
                        ...prep,
                        injection_order_numbers: { ...prep.injection_order_numbers, [solution]: Number(e.target.value) },
                      },
                    }))}
                    className="rounded-lg border border-slate-300 px-3 py-2"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    if (step.step_type === 'transfer' || step.step_type === 'evacuate') {
      return (
        <div className="grid gap-4 md:grid-cols-2">
          <NumberField label="泵地址" value={step.pump_address} min={1} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, pump_address: value }))} />
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">泵方向</span>
            <select
              value={step.pump_direction}
              onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, pump_direction: e.target.value as 'FWD' | 'REV' }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            >
              <option value="FWD">FWD</option>
              <option value="REV">REV</option>
            </select>
          </label>
          <NumberField label="泵转速" value={step.pump_rpm} unit="rpm" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, pump_rpm: value }))} />
          <NumberField label="体积模式" value={step.volume_ul} unit="μL" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, volume_ul: value }))} />
          <NumberField label="时长模式" value={step.transfer_duration} min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, transfer_duration: value }))} />
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">时长单位</span>
            <select
              value={step.transfer_duration_unit}
              onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, transfer_duration_unit: e.target.value as ExperimentStep['transfer_duration_unit'] }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            >
              <option value="ms">ms</option>
              <option value="s">s</option>
              <option value="min">min</option>
              <option value="hr">hr</option>
              <option value="cycle">cycle</option>
            </select>
          </label>
        </div>
      );
    }

    if (step.step_type === 'flush') {
      return (
        <div className="grid gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">Flush channel</span>
            <input
              type="text"
              value={step.flush_channel_id ?? ''}
              onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, flush_channel_id: e.target.value }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            />
          </label>
          <NumberField label="冲洗转速" value={step.flush_rpm} unit="rpm" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_rpm: value }))} />
          <NumberField label="每轮时长" value={step.flush_cycle_duration_s} unit="s" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_cycle_duration_s: value }))} />
          <NumberField label="循环次数" value={step.flush_cycles} min={1} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_cycles: value }))} />
        </div>
      );
    }

    if (step.step_type === 'echem') {
      const ec = step.ec_settings!;
      const fields = TECHNIQUE_FIELDS[ec.technique] ?? [];
      return (
        <div className="space-y-4">
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">Technique</span>
            <select
              value={ec.technique}
              onChange={(e) => updateStep(step.step_id, (current) => ({
                ...current,
                ec_settings: { ...ec, technique: e.target.value as EchemTechnique },
              }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            >
              <option value="CV">CV</option>
              <option value="LSV">LSV</option>
              <option value="i-t">i-t</option>
              <option value="EIS">EIS</option>
              <option value="ADT">ADT</option>
            </select>
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            {fields.map((field) => (
              <NumberField
                key={field.key}
                label={field.label}
                unit={field.unit}
                value={ec[field.key as keyof typeof ec] as number | undefined}
                onChange={(value) => updateStep(step.step_id, (current) => ({
                  ...current,
                  ec_settings: { ...ec, [field.key]: value },
                }))}
              />
            ))}
          </div>
        </div>
      );
    }

    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
        blank 步骤当前只保留备注与占位能力，后续可继续补 duration / confirmation gate。
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[94vh] w-full max-w-7xl overflow-y-auto rounded-3xl bg-slate-50 shadow-2xl">
        <div className="border-b border-slate-200 bg-white px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-blue-600">Experiment step editor</p>
              <h3 className="mt-1 text-2xl font-bold text-slate-900">创建真实 Experiment.steps[]，不是 technique 向导</h3>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
                先填实验级信息，再按 step_type 逐步编排步骤。当前已覆盖 prep_sol / transfer / flush / echem / blank / evacuate 六类步骤，并提供动态表单骨架。
              </p>
            </div>
            <button onClick={onClose} className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="grid gap-6 px-6 py-6 xl:grid-cols-[0.95fr,1.35fr,1fr]">
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div>
              <h4 className="text-lg font-semibold text-slate-900">实验级信息</h4>
              <p className="mt-1 text-sm text-slate-600">名称、描述、tags、operator 在这里统一管理。</p>
            </div>

            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
            )}

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">实验名称</span>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：Fe3+ 配液 + CV 首轮筛选" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">实验描述</span>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="这轮实验想回答什么问题、如何判断成败、需要重点观察什么。" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">Operator</span>
              <input value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="例如：boss / auto-run / design-agent" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">Tags</span>
              <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="逗号分隔，例如：Fe3+, screening, CV" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4" />
                <div>
                  <p className="font-semibold">执行前风险提示</p>
                  <ul className="mt-2 space-y-1">
                    {riskHints.length > 0 ? riskHints.map((hint) => <li key={hint}>• {hint}</li>) : <li>• 当前骨架可提交；后续可继续补更严格的 schema 校验。</li>}
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h4 className="text-lg font-semibold text-slate-900">步骤编排区</h4>
                <p className="mt-1 text-sm text-slate-600">支持添加、排序、复制、删除；右侧会显示当前步骤的动态表单。</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {(['prep_sol', 'transfer', 'flush', 'echem', 'blank', 'evacuate'] as StepType[]).map((type) => (
                  <button key={type} type="button" onClick={() => addStep(type)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50">
                    + {type}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              {steps.map((step, index) => {
                const meta = STEP_META[step.step_type];
                const Icon = meta.icon;
                const active = step.step_id === expandedStepId;
                return (
                  <div key={step.step_id} className={`rounded-2xl border p-4 transition ${active ? 'border-blue-400 bg-blue-50/40' : 'border-slate-200 bg-slate-50'}`}>
                    <div className="flex items-start justify-between gap-3">
                      <button type="button" onClick={() => setExpandedStepId(step.step_id)} className="flex flex-1 items-start gap-3 text-left">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm">
                          <Icon className="h-5 w-5 text-slate-700" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-semibold text-slate-900">Step {index + 1}</span>
                            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${meta.tone}`}>{step.step_type}</span>
                          </div>
                          <p className="mt-1 text-sm font-medium text-slate-800">{meta.label}</p>
                          <p className="mt-1 text-xs leading-5 text-slate-500">{formatStepSummary(step)}</p>
                        </div>
                      </button>
                      <div className="flex items-center gap-1">
                        <button onClick={() => moveStep(index, -1)} disabled={index === 0} className="rounded-lg p-2 text-slate-500 hover:bg-white disabled:opacity-30"><ArrowUp className="h-4 w-4" /></button>
                        <button onClick={() => moveStep(index, 1)} disabled={index === steps.length - 1} className="rounded-lg p-2 text-slate-500 hover:bg-white disabled:opacity-30"><ArrowDown className="h-4 w-4" /></button>
                        <button onClick={() => duplicateStep(index)} className="rounded-lg p-2 text-slate-500 hover:bg-white"><Plus className="h-4 w-4" /></button>
                        <button onClick={() => removeStep(step.step_id)} className="rounded-lg p-2 text-red-500 hover:bg-red-50"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h4 className="text-lg font-semibold text-slate-900">步骤参数编辑区</h4>
              {activeStep ? (
                <div className="mt-4 space-y-4">
                  <label>
                    <span className="mb-1 block text-sm font-medium text-slate-700">Step type</span>
                    <select
                      value={activeStep.step_type}
                      onChange={(e) => updateStep(activeStep.step_id, (current) => ({ ...current, step_type: e.target.value as StepType }))}
                      className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                    >
                      {Object.keys(STEP_META).map((type) => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className="mb-1 block text-sm font-medium text-slate-700">备注 / summary</span>
                    <textarea
                      value={activeStep.notes}
                      onChange={(e) => updateStep(activeStep.step_id, (current) => ({ ...current, notes: e.target.value }))}
                      rows={3}
                      className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
                      placeholder="例如：先配 10 mL buffer，再转移到检测池做 CV。"
                    />
                  </label>
                  {renderStepForm(activeStep)}
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500">请选择一个步骤开始编辑。</div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-900 p-5 text-white shadow-sm">
              <button type="button" onClick={() => setShowJsonPreview((prev) => !prev)} className="flex w-full items-center justify-between text-left">
                <div>
                  <p className="text-sm font-medium text-blue-200">执行前预览</p>
                  <h4 className="mt-1 text-lg font-semibold">Experiment JSON 草案</h4>
                </div>
                {showJsonPreview ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {showJsonPreview && (
                <pre className="mt-4 max-h-[360px] overflow-auto rounded-xl bg-black/20 p-4 text-xs leading-6 text-slate-100">{JSON.stringify(experimentDraft, null, 2)}</pre>
              )}
            </div>
          </section>
        </div>

        <div className="flex flex-col gap-3 border-t border-slate-200 bg-white px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-500">当前共 <span className="font-semibold text-slate-800">{steps.length}</span> 个步骤，已对齐真实 step_type 编排模型。</div>
          <div className="flex gap-3">
            <button onClick={onClose} className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50">取消</button>
            <button onClick={handleSubmit} disabled={submitting} className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-700 disabled:bg-blue-400">
              <CheckCircle2 className="h-4 w-4" />
              {submitting ? '创建中...' : '创建实验并进入详情'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
