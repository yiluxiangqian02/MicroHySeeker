import { useEffect, useMemo, useState } from 'react';
import { useSystemConfigStore } from '@/stores/systemConfigStore';
import type { SystemConfig, DilutionChannel, FlushChannelCfg, PumpCfg } from '@/stores/systemConfigStore';
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
  Loader2,
  Plus,
  Trash2,
  Wind,
  X,
} from 'lucide-react';

type StepType = 'prep_sol' | 'transfer' | 'flush' | 'echem' | 'blank' | 'evacuate';
type EchemTechnique = 'CV' | 'LSV' | 'i-t' | 'EIS' | 'ADT';

/* ---------- experiment step ---------- */
type ExperimentStep = {
  step_id: string;
  step_type: StepType;
  notes: string;
  parallel_group?: number;
  /* transfer / evacuate */
  pump_address?: number;
  pump_direction?: 'FWD' | 'REV';
  pump_rpm?: number;
  volume_ul?: number;
  transfer_duration?: number;
  transfer_duration_unit?: 'ms' | 's' | 'min' | 'hr' | 'cycle';
  /* flush */
  flush_channel_id?: string;
  flush_rpm?: number;
  flush_cycle_duration_s?: number;
  flush_cycles?: number;
  /* blank */
  duration_s?: number;
  /* prep_sol */
  prep_sol_params?: {
    total_volume_ul: number;
    selected_solutions: Record<string, boolean>;
    target_concentrations: Record<string, number>;
    solvent_flags: Record<string, boolean>;
    injection_order_numbers: Record<string, number>;
    injection_order: string[];
  };
  /* echem — all fields from MicroHySeeker ECSettings */
  ec_settings?: {
    technique: EchemTechnique;
    e0?: number;
    eh?: number;
    el?: number;
    ef?: number;
    scan_rate?: number;
    sample_interval_ms?: number;
    sensitivity?: number;
    autosensitivity?: boolean;
    quiet_time_s?: number;
    run_time_s?: number;
    seg_num?: number;
    scan_dir?: string;
    /* EIS */
    freq_low?: number;
    freq_high?: number;
    amplitude?: number;
    bias_mode?: number;
    /* dummy cell */
    use_dummy_cell?: boolean;
    /* ADT common */
    adt_enabled?: boolean;
    adt_num_cycles?: number;
    /* ADT CP */
    adt_cathodic_current_mA?: number;
    adt_cp_anodic_current_mA?: number;
    adt_cp_e_high?: number;
    adt_cp_e_low?: number;
    adt_cp_high_e_hold_time?: number;
    adt_cp_low_e_hold_time?: number;
    adt_cathodic_duration_s?: number;
    adt_cp_anodic_time_s?: number;
    adt_cp_polarity?: string;
    adt_cp_sample_interval?: number;
    adt_cp_segments?: number;
    adt_cp_priority?: string;
    /* ADT CA */
    adt_anodic_potential_V?: number;
    adt_ca_e_high?: number;
    adt_ca_e_low?: number;
    adt_ca_polarity?: string;
    adt_ca_steps?: number;
    adt_anodic_duration_s?: number;
    adt_ca_sample_interval?: number;
    adt_ca_quiet_time?: number;
    adt_ca_sensitivity?: number;
    /* iR compensation */
    ir_compensation_enabled?: boolean;
    ir_compensation_ohm?: number;
  };
};

interface ExperimentCreateDialogProps {
  onClose: () => void;
  onSubmit: (experiment: Record<string, unknown>) => void;
}

const STEP_META: Record<StepType, { label: string; description: string; icon: typeof FlaskConical; tone: string; leftBorder: string }> = {
  prep_sol: {
    label: '配液',
    description: '设置溶液配比、浓度和注液顺序。',
    icon: Beaker,
    tone: 'bg-violet-50 text-violet-700 border-violet-200',
    leftBorder: 'border-l-violet-500',
  },
  transfer: {
    label: '移液',
    description: '通过泵按体积或时长完成液体转移。',
    icon: ArrowUp,
    tone: 'bg-sky-50 text-sky-700 border-sky-200',
    leftBorder: 'border-l-sky-500',
  },
  flush: {
    label: '冲洗',
    description: '通过指定通道循环冲洗管路。',
    icon: Droplets,
    tone: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    leftBorder: 'border-l-cyan-500',
  },
  echem: {
    label: '电化学',
    description: '配置电化学测量参数（CV、LSV、i-t、EIS、ADT）。',
    icon: FlaskConical,
    tone: 'bg-blue-50 text-blue-700 border-blue-200',
    leftBorder: 'border-l-blue-600',
  },
  blank: {
    label: '空白',
    description: '用于等待、观察或流程分段。',
    icon: ChevronRight,
    tone: 'bg-slate-50 text-slate-700 border-slate-200',
    leftBorder: 'border-l-slate-400',
  },
  evacuate: {
    label: '排空',
    description: '排空管路或容器中的残留液体。',
    icon: Wind,
    tone: 'bg-amber-50 text-amber-700 border-amber-200',
    leftBorder: 'border-l-amber-500',
  },
};

/* ---------- technique field definitions (matches MicroHySeeker ECSettings) ---------- */
type FieldDef = { key: string; label: string; unit?: string; type?: 'number' | 'select' | 'checkbox'; options?: { value: string; label: string }[] };

const CV_FIELDS: FieldDef[] = [
  { key: 'e0', label: '初始电位 E0', unit: 'V' },
  { key: 'eh', label: '上限电位 Eh', unit: 'V' },
  { key: 'el', label: '下限电位 El', unit: 'V' },
  { key: 'ef', label: '终止电位 Ef', unit: 'V' },
  { key: 'scan_rate', label: '扫描速率', unit: 'V/s' },
  { key: 'seg_num', label: '扫描段数' },
  { key: 'scan_dir', label: '扫描方向', type: 'select', options: [{ value: 'FWD', label: '正向 (FWD)' }, { value: 'REV', label: '反向 (REV)' }] },
  { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
  { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  { key: 'sensitivity', label: '灵敏度', unit: 'A/V' },
  { key: 'autosensitivity', label: '自动灵敏度', type: 'checkbox' },
];

const LSV_FIELDS: FieldDef[] = [
  { key: 'e0', label: '初始电位 E0', unit: 'V' },
  { key: 'ef', label: '终止电位 Ef', unit: 'V' },
  { key: 'scan_rate', label: '扫描速率', unit: 'V/s' },
  { key: 'scan_dir', label: '扫描方向', type: 'select', options: [{ value: 'FWD', label: '正向 (FWD)' }, { value: 'REV', label: '反向 (REV)' }] },
  { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
  { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  { key: 'sensitivity', label: '灵敏度', unit: 'A/V' },
  { key: 'autosensitivity', label: '自动灵敏度', type: 'checkbox' },
];

const IT_FIELDS: FieldDef[] = [
  { key: 'e0', label: '恒电位 E0', unit: 'V' },
  { key: 'run_time_s', label: '运行时间', unit: 's' },
  { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
  { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  { key: 'sensitivity', label: '灵敏度', unit: 'A/V' },
  { key: 'autosensitivity', label: '自动灵敏度', type: 'checkbox' },
];

const EIS_FIELDS: FieldDef[] = [
  { key: 'e0', label: '初始电位 E0', unit: 'V' },
  { key: 'freq_high', label: '高频率', unit: 'Hz' },
  { key: 'freq_low', label: '低频率', unit: 'Hz' },
  { key: 'amplitude', label: '交流振幅', unit: 'V' },
  { key: 'bias_mode', label: '偏置模式', type: 'select', options: [{ value: '0', label: 'vs Eref' }, { value: '1', label: 'vs Eoc' }] },
  { key: 'quiet_time_s', label: '静置时间', unit: 's' },
];

const ADT_COMMON_FIELDS: FieldDef[] = [
  { key: 'adt_num_cycles', label: 'ADT 循环轮数' },
];

const ADT_CP_FIELDS: FieldDef[] = [
  { key: 'adt_cathodic_current_mA', label: '阴极电流 ic', unit: 'mA' },
  { key: 'adt_cp_anodic_current_mA', label: '阳极电流 ia', unit: 'mA' },
  { key: 'adt_cathodic_duration_s', label: '阴极时间 tc', unit: 's' },
  { key: 'adt_cp_anodic_time_s', label: '阳极时间 ta', unit: 's' },
  { key: 'adt_cp_e_high', label: 'CP 电位上限 eh', unit: 'V' },
  { key: 'adt_cp_e_low', label: 'CP 电位下限 el', unit: 'V' },
  { key: 'adt_cp_high_e_hold_time', label: '高电位保持时间', unit: 's' },
  { key: 'adt_cp_low_e_hold_time', label: '低电位保持时间', unit: 's' },
  { key: 'adt_cp_polarity', label: 'CP 首步极性', type: 'select', options: [{ value: 'n', label: '阴极先 (n)' }, { value: 'p', label: '阳极先 (p)' }] },
  { key: 'adt_cp_sample_interval', label: 'CP 采样间隔', unit: 's' },
  { key: 'adt_cp_segments', label: 'CP 段数' },
  { key: 'adt_cp_priority', label: 'CP 优先级', type: 'select', options: [{ value: 'time', label: '时间优先' }, { value: 'potential', label: '电位优先' }] },
];

const ADT_CA_FIELDS: FieldDef[] = [
  { key: 'adt_anodic_potential_V', label: 'CA 初始电位 ei', unit: 'V' },
  { key: 'adt_ca_e_high', label: 'CA 高电位限 eh', unit: 'V' },
  { key: 'adt_ca_e_low', label: 'CA 低电位限 el', unit: 'V' },
  { key: 'adt_ca_polarity', label: 'CA 方向', type: 'select', options: [{ value: 'p', label: '正向 (p)' }, { value: 'n', label: '负向 (n)' }] },
  { key: 'adt_ca_steps', label: 'CA 阶跃数' },
  { key: 'adt_anodic_duration_s', label: 'CA 脉冲宽度', unit: 's' },
  { key: 'adt_ca_sample_interval', label: 'CA 采样间隔', unit: 's' },
  { key: 'adt_ca_quiet_time', label: 'CA 静置时间', unit: 's' },
  { key: 'adt_ca_sensitivity', label: 'CA 灵敏度', unit: 'A/V' },
];

const TECHNIQUE_FIELDS: Record<EchemTechnique, FieldDef[]> = {
  CV: CV_FIELDS,
  LSV: LSV_FIELDS,
  'i-t': IT_FIELDS,
  EIS: EIS_FIELDS,
  ADT: ADT_COMMON_FIELDS,
};

const IR_FIELDS: FieldDef[] = [
  { key: 'ir_compensation_enabled', label: 'iR 补偿', type: 'checkbox' },
  { key: 'ir_compensation_ohm', label: '补偿电阻', unit: 'Ω' },
];

const DUMMY_CELL_FIELD: FieldDef = { key: 'use_dummy_cell', label: 'Dummy Cell 测试模式', type: 'checkbox' };

function createStep(type: StepType = 'prep_sol', index = 0, solutionNames: string[] = []): ExperimentStep {
  return {
    step_id: `step_${Date.now()}_${index}`,
    step_type: type,
    notes: '',
    parallel_group: 0,
    pump_address: 1,
    pump_direction: 'FWD',
    pump_rpm: 120,
    volume_ul: 1000,
    transfer_duration: 30,
    transfer_duration_unit: 's',
    flush_channel_id: '',
    flush_rpm: 100,
    flush_cycle_duration_s: 30,
    flush_cycles: 1,
    duration_s: 60,
    prep_sol_params: {
      total_volume_ul: 100000,
      selected_solutions: Object.fromEntries(solutionNames.map((name, idx) => [name, idx < 2])),
      target_concentrations: Object.fromEntries(solutionNames.map((name) => [name, 0])),
      solvent_flags: Object.fromEntries(solutionNames.map((name, idx) => [name, idx === solutionNames.length - 1])),
      injection_order_numbers: Object.fromEntries(solutionNames.map((name, idx) => [name, idx + 1])),
      injection_order: solutionNames,
    },
    ec_settings: {
      technique: 'CV',
      e0: 0, eh: 0.8, el: -0.2, ef: 0,
      scan_rate: 0.05, sample_interval_ms: 100,
      sensitivity: undefined, autosensitivity: false,
      quiet_time_s: 2, seg_num: 2, scan_dir: 'FWD',
      run_time_s: 60,
      /* EIS */
      freq_low: 1, freq_high: 100000, amplitude: 0.005, bias_mode: 0,
      /* dummy cell */
      use_dummy_cell: false,
      /* ADT common */
      adt_enabled: false, adt_num_cycles: 100,
      /* ADT CP */
      adt_cathodic_current_mA: -250, adt_cp_anodic_current_mA: 250,
      adt_cp_e_high: 2.0, adt_cp_e_low: -2.0,
      adt_cp_high_e_hold_time: 0, adt_cp_low_e_hold_time: 0,
      adt_cathodic_duration_s: 3.0, adt_cp_anodic_time_s: 3.0,
      adt_cp_polarity: 'n', adt_cp_sample_interval: 0.01,
      adt_cp_segments: 2, adt_cp_priority: 'time',
      /* ADT CA */
      adt_anodic_potential_V: 1.5,
      adt_ca_e_high: 1.5, adt_ca_e_low: -0.5,
      adt_ca_polarity: 'p', adt_ca_steps: 1,
      adt_anodic_duration_s: 2.0, adt_ca_sample_interval: 0.01,
      adt_ca_quiet_time: 0, adt_ca_sensitivity: 0.001,
      /* iR compensation */
      ir_compensation_enabled: false, ir_compensation_ohm: 0,
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
      return step.volume_ul ? `${step.volume_ul} μL · 泵${step.pump_address}` : `${step.transfer_duration ?? 0} ${step.transfer_duration_unit ?? 's'} · 泵${step.pump_address}`;
    case 'flush':
      return `${step.flush_channel_id ?? '未选通道'} · ${step.flush_cycles ?? 1} 次循环`;
    case 'echem':
      return `${step.ec_settings?.technique ?? 'CV'} · 采样间隔 ${step.ec_settings?.sample_interval_ms ?? 100} ms`;
    case 'blank':
      return step.duration_s ? `等待 ${step.duration_s} s` : (step.notes || '空白等待');
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
  const [category, setCategory] = useState<'test' | 'formal' | 'calibration'>('test');
  const [showJsonPreview, setShowJsonPreview] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  /* ---------- system config (from global store, preloaded on app start) ---------- */
  const storeConfig = useSystemConfigStore((s) => s.config);
  const storeLoading = useSystemConfigStore((s) => s.loading);
  const fetchConfig = useSystemConfigStore((s) => s.fetchConfig);
  const mhsStatus = useSystemConfigStore((s) => s.mhsStatus);
  const fetchMHSStatus = useSystemConfigStore((s) => s.fetchMHSStatus);

  // 如果 store 还没加载过，触发一次
  useEffect(() => { if (!storeConfig && !storeLoading) fetchConfig(); }, [storeConfig, storeLoading, fetchConfig]);
  // 每次打开对话框时刷新 MHS 状态
  useEffect(() => { fetchMHSStatus(); }, [fetchMHSStatus]);

  const sysCfg = storeConfig;
  const cfgLoading = storeLoading && !storeConfig;

  const solutionNames = useMemo(() => {
    const names = sysCfg?.dilution_channels?.map((ch) => ch.solution_name) ?? [];
    // H₂O 溶剂由 MHS Inlet flush channel 提供，始终追加
    if (names.length > 0 && !names.includes('H2O')) names.push('H2O');
    return names;
  }, [sysCfg]);
  const dilutionMap = useMemo(() => {
    const m: Record<string, DilutionChannel> = {};
    for (const ch of sysCfg?.dilution_channels ?? []) m[ch.solution_name] = ch;
    return m;
  }, [sysCfg]);
  const flushChannels = useMemo(() => sysCfg?.flush_channels ?? [], [sysCfg]);
  const pumps = useMemo(() => sysCfg?.pumps ?? [], [sysCfg]);

  /* ---------- templates (preloaded on dialog open) ---------- */
  const [templates, setTemplates] = useState<Array<{ template_id: string; name: string; description: string; steps: any[]; tags: string[] }>>([]);
  useEffect(() => {
    (async () => {
      try {
        const resp = await fetch('/api/templates');
        if (resp.ok) setTemplates(await resp.json());
      } catch { /* ignore */ }
    })();
  }, []);

  const loadTemplate = (tpl: typeof templates[0]) => {
    if (!tpl.steps?.length) return;
    const mapped: ExperimentStep[] = tpl.steps.map((s: any, idx: number) => {
      const params = s.params ?? s;
      const base = createStep((s.step_type ?? 'blank') as StepType, idx, solutionNames);
      return { ...base, ...params, step_id: `tpl_${Date.now()}_${idx}` };
    });
    setSteps(mapped);
    if (!name) setName(tpl.name);
    if (!description) setDescription(tpl.description ?? '');
    setExpandedStepId(mapped[0]?.step_id ?? null);
  };

  const [steps, setSteps] = useState<ExperimentStep[]>([]);
  const [expandedStepId, setExpandedStepId] = useState<string | null>(null);

  // Initialize steps once config is loaded
  useEffect(() => {
    if (!cfgLoading && steps.length === 0) {
      const init = [createStep('prep_sol', 0, solutionNames), createStep('echem', 1, solutionNames)];
      setSteps(init);
      setExpandedStepId(init[0].step_id);
    }
  }, [cfgLoading, solutionNames, steps.length]);

  const activeIndex = Math.max(0, steps.findIndex((step) => step.step_id === expandedStepId));
  const activeStep = steps[activeIndex] ?? null;

  const updateStep = (stepId: string, updater: (step: ExperimentStep) => ExperimentStep) => {
    setSteps((prev) => prev.map((step) => (step.step_id === stepId ? updater(step) : step)));
  };

  const addStep = (type: StepType = 'blank') => {
    const next = createStep(type, steps.length, solutionNames);
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
    if (!steps.some((step) => step.step_type === 'echem')) hints.push('当前方案无电化学步骤，将无法采集电化学数据。');
    if (steps.some((step) => step.step_type === 'transfer' && !step.volume_ul && !step.transfer_duration)) {
      hints.push('移液步骤未设置体积或持续时间。');
    }
    if (steps.some((step) => step.step_type === 'prep_sol' && !Object.values(step.prep_sol_params?.selected_solutions ?? {}).some(Boolean))) {
      hints.push('配液步骤未选中任何溶液。');
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
        category,
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
          {solutionNames.length === 0 ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              未检测到配液通道。请确认 MicroHySeeker 已配置 dilution_channels。
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200">
              <div className="grid grid-cols-[1fr,0.7fr,0.5fr,0.7fr,0.5fr,0.5fr] gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2.5 text-xs font-semibold text-slate-500">
                <span>溶液名称</span>
                <span>原浓度 (mol/L)</span>
                <span>泵端口</span>
                <span>目标浓度 (mol/L)</span>
                <span>溶剂</span>
                <span>注液顺序</span>
              </div>
              <div className="divide-y divide-slate-100">
                {solutionNames.map((solution) => {
                  const ch = dilutionMap[solution];
                  return (
                    <div key={solution} className="grid grid-cols-[1fr,0.7fr,0.5fr,0.7fr,0.5fr,0.5fr] gap-2 px-3 py-2.5 text-sm text-slate-700 items-center">
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
                        <span className="font-medium">{solution}</span>
                      </label>
                      <span className="text-slate-500">{ch?.stock_concentration ?? '—'}</span>
                      <span className="text-slate-500">{ch?.pump_address ?? '—'}</span>
                      <input
                        type="number"
                        step="0.001"
                        value={prep.target_concentrations[solution] ?? 0}
                        onChange={(e) => updateStep(step.step_id, (current) => ({
                          ...current,
                          prep_sol_params: {
                            ...prep,
                            target_concentrations: { ...prep.target_concentrations, [solution]: Number(e.target.value) },
                          },
                        }))}
                        className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                      />
                      <label className="flex items-center gap-1">
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
                        <span className="text-xs">是</span>
                      </label>
                      <input
                        type="number"
                        min={1}
                        value={prep.injection_order_numbers[solution] ?? 1}
                        onChange={(e) => updateStep(step.step_id, (current) => ({
                          ...current,
                          prep_sol_params: {
                            ...prep,
                            injection_order_numbers: { ...prep.injection_order_numbers, [solution]: Number(e.target.value) },
                          },
                        }))}
                        className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      );
    }

    if (step.step_type === 'transfer' || step.step_type === 'evacuate') {
      return (
        <div className="grid gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">泵地址</span>
            <select
              value={step.pump_address ?? 1}
              onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, pump_address: Number(e.target.value) }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            >
              {pumps.length > 0
                ? pumps.map((p) => <option key={p.address} value={p.address}>{p.address} — {p.name}</option>)
                : Array.from({ length: 12 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">方向</span>
            <select
              value={step.pump_direction}
              onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, pump_direction: e.target.value as 'FWD' | 'REV' }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            >
              <option value="FWD">FWD</option>
              <option value="REV">REV</option>
            </select>
          </label>
          <NumberField label="转速" value={step.pump_rpm} unit="RPM" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, pump_rpm: value }))} />
          <NumberField label="体积" value={step.volume_ul} unit="μL" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, volume_ul: value }))} />
          <NumberField label="持续时间" value={step.transfer_duration} min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, transfer_duration: value }))} />
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">时间单位</span>
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
          {step.step_type === 'evacuate' && (
            <NumberField label="排空次数" value={step.flush_cycles ?? 1} min={1} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_cycles: value }))} />
          )}
        </div>
      );
    }

    if (step.step_type === 'flush') {
      return (
        <div className="grid gap-4 md:grid-cols-2">
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">冲洗通道</span>
            {flushChannels.length > 0 ? (
              <select
                value={step.flush_channel_id ?? ''}
                onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, flush_channel_id: e.target.value }))}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
              >
                <option value="">请选择冲洗通道</option>
                {flushChannels.map((ch) => (
                  <option key={ch.channel_id} value={ch.channel_id}>
                    {ch.pump_name} (泵{ch.pump_address}, {ch.work_type})
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={step.flush_channel_id ?? ''}
                onChange={(e) => updateStep(step.step_id, (current) => ({ ...current, flush_channel_id: e.target.value }))}
                className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                placeholder="通道ID"
              />
            )}
          </label>
          <NumberField label="转速" value={step.flush_rpm} unit="RPM" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_rpm: value }))} />
          <NumberField label="单次时长" value={step.flush_cycle_duration_s} unit="s" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_cycle_duration_s: value }))} />
          <NumberField label="循环次数" value={step.flush_cycles} min={1} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, flush_cycles: value }))} />
        </div>
      );
    }

    if (step.step_type === 'echem') {
      const ec = step.ec_settings!;
      const techFields = TECHNIQUE_FIELDS[ec.technique] ?? [];
      return (
        <div className="space-y-4">
          <label>
            <span className="mb-1 block text-sm font-medium text-slate-700">测量技术</span>
            <select
              value={ec.technique}
              onChange={(e) => updateStep(step.step_id, (current) => ({
                ...current,
                ec_settings: { ...ec, technique: e.target.value as EchemTechnique },
              }))}
              className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
            >
              <option value="CV">CV — 循环伏安</option>
              <option value="LSV">LSV — 线性扫描</option>
              <option value="i-t">i-t — 计时电流</option>
              <option value="EIS">EIS — 交流阻抗</option>
              <option value="ADT">ADT — 加速耐久</option>
            </select>
          </label>

          {/* technique-specific fields */}
          <div className="grid gap-3 md:grid-cols-2">
            {techFields.map((fd) => renderEcField(fd, ec, step.step_id))}
          </div>

          {/* ADT: CP and CA sub-sections */}
          {ec.technique === 'ADT' && (
            <>
              <div className="mt-2 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
                <h5 className="text-sm font-semibold text-indigo-800 mb-3">CP 计时电位法参数</h5>
                <div className="grid gap-3 md:grid-cols-2">
                  {ADT_CP_FIELDS.map((fd) => renderEcField(fd, ec, step.step_id))}
                </div>
              </div>
              <div className="mt-2 rounded-xl border border-teal-200 bg-teal-50 p-4">
                <h5 className="text-sm font-semibold text-teal-800 mb-3">CA 计时电流法参数</h5>
                <div className="grid gap-3 md:grid-cols-2">
                  {ADT_CA_FIELDS.map((fd) => renderEcField(fd, ec, step.step_id))}
                </div>
              </div>
            </>
          )}

          {/* iR compensation + dummy cell */}
          <div className="grid gap-3 md:grid-cols-2 mt-2">
            {IR_FIELDS.map((fd) => renderEcField(fd, ec, step.step_id))}
            {renderEcField(DUMMY_CELL_FIELD, ec, step.step_id)}
          </div>
        </div>
      );
    }

    if (step.step_type === 'blank') {
      return (
        <div className="space-y-4">
          <NumberField label="等待时间" value={step.duration_s} unit="s" min={0} onChange={(value) => updateStep(step.step_id, (current) => ({ ...current, duration_s: value }))} />
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-600">
            空白步骤用于等待、观察或流程分段，可在备注中记录说明。
          </div>
        </div>
      );
    }

    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600">
        排空步骤：排空管路或容器中的残留液体。
      </div>
    );
  };

  /* helper: render a single ec_settings field */
  const renderEcField = (fd: FieldDef, ec: NonNullable<ExperimentStep['ec_settings']>, stepId: string) => {
    const val = ec[fd.key as keyof typeof ec];
    if (fd.type === 'checkbox') {
      return (
        <label key={fd.key} className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={!!val}
            onChange={(e) => updateStep(stepId, (current) => ({
              ...current,
              ec_settings: { ...ec, [fd.key]: e.target.checked },
            }))}
          />
          <span>{fd.label}</span>
        </label>
      );
    }
    if (fd.type === 'select') {
      return (
        <label key={fd.key} className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700">{fd.label}</span>
          <select
            value={String(val ?? fd.options?.[0]?.value ?? '')}
            onChange={(e) => {
              const v = fd.key === 'bias_mode' ? Number(e.target.value) : e.target.value;
              updateStep(stepId, (current) => ({ ...current, ec_settings: { ...ec, [fd.key]: v } }));
            }}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
          >
            {fd.options?.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </label>
      );
    }
    return (
      <NumberField
        key={fd.key}
        label={fd.label}
        unit={fd.unit}
        value={val as number | undefined}
        onChange={(v) => updateStep(stepId, (current) => ({ ...current, ec_settings: { ...ec, [fd.key]: v } }))}
      />
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="max-h-[94vh] w-full max-w-7xl overflow-y-auto rounded-3xl bg-slate-50 shadow-2xl">
        <div className="border-b border-slate-200 bg-white px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-blue-600">实验步骤编辑器</p>
              <h3 className="mt-1 text-2xl font-bold text-slate-900">创建实验</h3>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600">
                填写实验基本信息，然后逐步编排操作步骤。支持配液、移液、冲洗、电化学、空白、排空六类步骤。
              </p>
            </div>
            <button onClick={onClose} className="rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* MHS 硬件连接状态横幅 */}
        <div className={`mx-6 mt-4 flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm ${
          mhsStatus.online
            ? mhsStatus.connected
              ? 'border-green-200 bg-green-50 text-green-800'
              : 'border-amber-200 bg-amber-50 text-amber-800'
            : 'border-red-200 bg-red-50 text-red-800'
        }`}>
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${
            mhsStatus.online ? (mhsStatus.connected ? 'bg-green-500' : 'bg-amber-500') : 'bg-red-500'
          }`} />
          <span className="font-medium">MHS</span>
          <span>{mhsStatus.online ? '在线' : '离线'}</span>
          {mhsStatus.online && (
            <>
              <span className="text-slate-300">|</span>
              <span>RS485: {mhsStatus.connected ? '已连接' : '未连接'}</span>
              {mhsStatus.port && (
                <>
                  <span className="text-slate-300">|</span>
                  <span className="font-mono font-semibold">{mhsStatus.port}</span>
                </>
              )}
              {mhsStatus.mock_mode && (
                <>
                  <span className="text-slate-300">|</span>
                  <span className="rounded bg-amber-200 px-1.5 py-0.5 text-xs font-medium">模拟模式</span>
                </>
              )}
            </>
          )}
        </div>

        <div className="grid gap-6 px-6 py-6 lg:grid-cols-[0.95fr,1.35fr,1fr]">
          {cfgLoading ? (
            <div className="col-span-3 flex items-center justify-center py-12 text-slate-500">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              正在加载系统配置...
            </div>
          ) : (
          <>
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div>
              <h4 className="text-lg font-semibold text-slate-900">基本信息</h4>
              <p className="mt-1 text-sm text-slate-600">填写实验名称、描述、操作员和标签。</p>
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
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="本次实验的目标、假设和观察重点。" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">操作员</span>
              <input value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="例如：boss / auto-run / design-agent" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">标签</span>
              <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="逗号分隔，例如：Fe3+, screening, CV" className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm" />
            </label>
            <div className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">实验分类</span>
              <div className="flex gap-3">
                {([['test', '测试实验'], ['formal', '正式实验'], ['calibration', '标定实验']] as const).map(([val, label]) => (
                  <button key={val} type="button" onClick={() => setCategory(val)} className={`rounded-lg border px-4 py-2 text-sm transition-colors ${category === val ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium' : 'border-slate-300 bg-white text-slate-600 hover:bg-slate-50'}`}>{label}</button>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4" />
                <div>
                  <p className="font-semibold">执行前风险提示</p>
                  <ul className="mt-2 space-y-1">
                    {riskHints.length > 0 ? riskHints.map((hint) => <li key={hint}>• {hint}</li>) : <li>• 当前方案可提交，请确认各步骤参数。</li>}
                  </ul>
                </div>
              </div>
            </div>
          </section>

          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h4 className="text-lg font-semibold text-slate-900">步骤列表</h4>
                <p className="mt-1 text-sm text-slate-600">添加、排序、复制或删除步骤，选中后在右侧编辑参数。</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {(['prep_sol', 'transfer', 'flush', 'echem', 'blank', 'evacuate'] as StepType[]).map((type) => (
                  <button key={type} type="button" onClick={() => addStep(type)} className={`rounded-full border px-3 py-1.5 text-xs font-medium transition hover:opacity-80 ${STEP_META[type].tone}`}>
                    + {STEP_META[type].label}
                  </button>
                ))}
              </div>
            </div>

            {templates.length > 0 && (
              <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-3">
                <span className="mb-1.5 block text-xs font-medium text-indigo-700">从模板加载步骤</span>
                <div className="flex gap-2">
                  <select
                    defaultValue=""
                    onChange={(e) => {
                      const tpl = templates.find((t) => t.template_id === e.target.value);
                      if (tpl) loadTemplate(tpl);
                      e.target.value = '';
                    }}
                    className="flex-1 rounded-lg border border-indigo-300 bg-white px-3 py-2 text-sm text-slate-700"
                  >
                    <option value="" disabled>选择模板…</option>
                    {templates.map((t) => (
                      <option key={t.template_id} value={t.template_id}>
                        {t.name}{t.tags?.includes('mhs') ? ' (MHS)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {steps.map((step, index) => {
                const meta = STEP_META[step.step_type];
                const Icon = meta.icon;
                const active = step.step_id === expandedStepId;
                return (
                  <div key={step.step_id} className={`rounded-2xl border-l-4 border border-l-[3px] p-4 transition ${active ? `border-l-blue-500 border-blue-300 bg-blue-50/40` : `${meta.leftBorder} border-slate-200 bg-white`}`}>
                    <div className="flex items-start justify-between gap-3">
                      <button type="button" onClick={() => setExpandedStepId(step.step_id)} className="flex flex-1 items-start gap-3 text-left">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white shadow-sm">
                          <Icon className="h-5 w-5 text-slate-700" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-semibold text-slate-900">Step {index + 1}</span>
                            <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${meta.tone}`}>{meta.label}</span>
                            {(step.parallel_group ?? 0) > 0 && <span className="rounded-full bg-orange-100 border border-orange-300 px-2 py-0.5 text-xs font-semibold text-orange-700">∥{step.parallel_group}</span>}
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
              <h4 className="text-lg font-semibold text-slate-900">参数编辑</h4>
              {activeStep ? (
                <div className="mt-4 space-y-4">
                  <label>
                    <span className="mb-1 block text-sm font-medium text-slate-700">步骤类型</span>
                    <select
                      value={activeStep.step_type}
                      onChange={(e) => updateStep(activeStep.step_id, (current) => ({ ...current, step_type: e.target.value as StepType }))}
                      className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm"
                    >
                      {(Object.keys(STEP_META) as StepType[]).map((type) => (
                        <option key={type} value={type}>{STEP_META[type].label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className="mb-1 block text-sm font-medium text-slate-700">备注</span>
                    <textarea
                      value={activeStep.notes}
                      onChange={(e) => updateStep(activeStep.step_id, (current) => ({ ...current, notes: e.target.value }))}
                      rows={3}
                      className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
                      placeholder="例如：配制 10 mL 缓冲液，转移至检测池进行 CV 扫描。"
                    />
                  </label>
                  <label>
                    <span className="mb-1 block text-sm font-medium text-slate-700">并行组</span>
                    <input
                      type="number"
                      value={activeStep.parallel_group ?? 0}
                      min={0}
                      max={99}
                      onChange={(e) => updateStep(activeStep.step_id, (current) => ({ ...current, parallel_group: Number(e.target.value) }))}
                      className="w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
                      title="0 = 串行执行；相同非零编号的步骤将同时执行"
                    />
                    <span className="mt-1 block text-xs text-slate-400">0 = 串行；相同非零编号 → 并行执行</span>
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
                  <h4 className="mt-1 text-lg font-semibold">实验数据预览</h4>
                </div>
                {showJsonPreview ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {showJsonPreview && (
                <pre className="mt-4 max-h-[360px] overflow-auto rounded-xl bg-black/20 p-4 text-xs leading-6 text-slate-100">{JSON.stringify(experimentDraft, null, 2)}</pre>
              )}
            </div>
          </section>
          </>
          )}
        </div>

        <div className="flex flex-col gap-3 border-t border-slate-200 bg-white px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-slate-500">当前共 <span className="font-semibold text-slate-800">{steps.length}</span> 个步骤</div>
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
