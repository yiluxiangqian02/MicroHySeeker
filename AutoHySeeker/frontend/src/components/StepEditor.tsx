/**
 * StepEditor — 与 MicroHySeeker ProgStep 数据模型完全同步的富文本步骤编辑器。
 * 支持 prep_sol / transfer / flush / echem / blank / evacuate 六类步骤，
 * 每类步骤有专属动态表单，与 MicroHySeeker models.py 字段一一对应。
 * 配液通道和冲洗通道从 /api/system/config 动态加载。
 */
import { useEffect, useMemo, useState } from 'react';
import {
  ArrowDown, ArrowUp, Beaker, ChevronRight, Droplets, FlaskConical,
  Loader2, Plus, Trash2, Wind,
} from 'lucide-react';

// ─── Types — 与 MicroHySeeker ProgStep / ECSettings / PrepSolStep 同步 ──────

type StepType = 'prep_sol' | 'transfer' | 'flush' | 'echem' | 'blank' | 'evacuate';
type EchemTechnique = 'CV' | 'LSV' | 'i-t' | 'EIS' | 'ADT';

interface DilutionChannel {
  channel_id: string;
  solution_name: string;
  stock_concentration: number;
  pump_address: number;
  direction: string;
  default_rpm: number;
}
interface FlushChannelCfg {
  channel_id: string;
  pump_name: string;
  pump_address: number;
  direction: string;
  rpm: number;
  cycle_duration_s: number;
  work_type: string;
}
interface PumpCfg { address: number; name: string; direction: string; default_rpm: number }
interface SysCfg {
  pumps: PumpCfg[];
  dilution_channels: DilutionChannel[];
  flush_channels: FlushChannelCfg[];
}

export type RichStep = {
  step_id: string;
  step_type: StepType;
  notes: string;
  parallel_group?: number;
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
  duration_s?: number;
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
    e0?: number; eh?: number; el?: number; ef?: number;
    scan_rate?: number; sample_interval_ms?: number;
    sensitivity?: number; autosensitivity?: boolean;
    quiet_time_s?: number; run_time_s?: number; seg_num?: number; scan_dir?: string;
    freq_low?: number; freq_high?: number; amplitude?: number; bias_mode?: number;
    use_dummy_cell?: boolean;
    adt_enabled?: boolean; adt_num_cycles?: number;
    adt_cathodic_current_mA?: number; adt_cp_anodic_current_mA?: number;
    adt_cp_e_high?: number; adt_cp_e_low?: number;
    adt_cp_high_e_hold_time?: number; adt_cp_low_e_hold_time?: number;
    adt_cathodic_duration_s?: number; adt_cp_anodic_time_s?: number;
    adt_cp_polarity?: string; adt_cp_sample_interval?: number;
    adt_cp_segments?: number; adt_cp_priority?: string;
    adt_anodic_potential_V?: number; adt_ca_e_high?: number; adt_ca_e_low?: number;
    adt_ca_polarity?: string; adt_ca_steps?: number;
    adt_anodic_duration_s?: number; adt_ca_sample_interval?: number;
    adt_ca_quiet_time?: number; adt_ca_sensitivity?: number;
    ir_compensation_enabled?: boolean; ir_compensation_ohm?: number;
  };
};

// ─── Meta ────────────────────────────────────────────────────────────────────

const STEP_META: Record<StepType, { label: string; icon: React.ComponentType<any>; tone: string; leftBorder: string }> = {
  prep_sol:  { label: '配液', icon: Beaker,       tone: 'bg-violet-50 text-violet-700 border-violet-200', leftBorder: 'border-l-violet-500' },
  transfer:  { label: '移液', icon: ArrowUp,      tone: 'bg-sky-50 text-sky-700 border-sky-200',          leftBorder: 'border-l-sky-500' },
  flush:     { label: '冲洗', icon: Droplets,     tone: 'bg-cyan-50 text-cyan-700 border-cyan-200',       leftBorder: 'border-l-cyan-500' },
  echem:     { label: '电化学', icon: FlaskConical, tone: 'bg-blue-50 text-blue-700 border-blue-200',      leftBorder: 'border-l-blue-600' },
  blank:     { label: '空白', icon: ChevronRight, tone: 'bg-slate-50 text-slate-700 border-slate-200',    leftBorder: 'border-l-slate-400' },
  evacuate:  { label: '排空', icon: Wind,         tone: 'bg-amber-50 text-amber-700 border-amber-200',    leftBorder: 'border-l-amber-500' },
};

type FD = { key: string; label: string; unit?: string; type?: 'number' | 'select' | 'checkbox'; options?: { value: string; label: string }[] };

const TECHNIQUE_FIELDS: Record<EchemTechnique, FD[]> = {
  CV: [
    { key: 'e0', label: '初始电位 E0', unit: 'V' },
    { key: 'eh', label: '上限电位 Eh', unit: 'V' },
    { key: 'el', label: '下限电位 El', unit: 'V' },
    { key: 'ef', label: '终止电位 Ef', unit: 'V' },
    { key: 'scan_rate', label: '扫描速率', unit: 'V/s' },
    { key: 'seg_num', label: '扫描段数' },
    { key: 'scan_dir', label: '扫描方向', type: 'select', options: [{ value: 'FWD', label: '正向' }, { value: 'REV', label: '反向' }] },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
    { key: 'sensitivity', label: '灵敏度', unit: 'A/V' },
    { key: 'autosensitivity', label: '自动灵敏度', type: 'checkbox' },
  ],
  LSV: [
    { key: 'e0', label: '初始电位 E0', unit: 'V' },
    { key: 'ef', label: '终止电位 Ef', unit: 'V' },
    { key: 'scan_rate', label: '扫描速率', unit: 'V/s' },
    { key: 'scan_dir', label: '扫描方向', type: 'select', options: [{ value: 'FWD', label: '正向' }, { value: 'REV', label: '反向' }] },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
    { key: 'sensitivity', label: '灵敏度', unit: 'A/V' },
    { key: 'autosensitivity', label: '自动灵敏度', type: 'checkbox' },
  ],
  'i-t': [
    { key: 'e0', label: '恒电位 E0', unit: 'V' },
    { key: 'run_time_s', label: '运行时间', unit: 's' },
    { key: 'sample_interval_ms', label: '采样间隔', unit: 'ms' },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
    { key: 'sensitivity', label: '灵敏度', unit: 'A/V' },
    { key: 'autosensitivity', label: '自动灵敏度', type: 'checkbox' },
  ],
  EIS: [
    { key: 'e0', label: '初始电位 E0', unit: 'V' },
    { key: 'freq_high', label: '高频率', unit: 'Hz' },
    { key: 'freq_low', label: '低频率', unit: 'Hz' },
    { key: 'amplitude', label: '交流振幅', unit: 'V' },
    { key: 'bias_mode', label: '偏置模式', type: 'select', options: [{ value: '0', label: 'vs Eref' }, { value: '1', label: 'vs Eoc' }] },
    { key: 'quiet_time_s', label: '静置时间', unit: 's' },
  ],
  ADT: [
    { key: 'adt_num_cycles', label: 'ADT 循环轮数' },
  ],
};

const ADT_CP_FIELDS: FD[] = [
  { key: 'adt_cathodic_current_mA', label: '阴极电流 ic', unit: 'mA' },
  { key: 'adt_cp_anodic_current_mA', label: '阳极电流 ia', unit: 'mA' },
  { key: 'adt_cathodic_duration_s', label: '阴极时间 tc', unit: 's' },
  { key: 'adt_cp_anodic_time_s', label: '阳极时间 ta', unit: 's' },
  { key: 'adt_cp_e_high', label: 'CP 电位上限', unit: 'V' },
  { key: 'adt_cp_e_low', label: 'CP 电位下限', unit: 'V' },
  { key: 'adt_cp_polarity', label: 'CP 首步极性', type: 'select', options: [{ value: 'n', label: '阴极先' }, { value: 'p', label: '阳极先' }] },
  { key: 'adt_cp_sample_interval', label: 'CP 采样间隔', unit: 's' },
  { key: 'adt_cp_segments', label: 'CP 段数' },
  { key: 'adt_cp_priority', label: 'CP 优先级', type: 'select', options: [{ value: 'time', label: '时间优先' }, { value: 'potential', label: '电位优先' }] },
];

const ADT_CA_FIELDS: FD[] = [
  { key: 'adt_anodic_potential_V', label: 'CA 初始电位', unit: 'V' },
  { key: 'adt_ca_e_high', label: 'CA 高电位限', unit: 'V' },
  { key: 'adt_ca_e_low', label: 'CA 低电位限', unit: 'V' },
  { key: 'adt_ca_polarity', label: 'CA 方向', type: 'select', options: [{ value: 'p', label: '正向' }, { value: 'n', label: '负向' }] },
  { key: 'adt_ca_steps', label: 'CA 阶跃数' },
  { key: 'adt_anodic_duration_s', label: 'CA 脉冲宽度', unit: 's' },
  { key: 'adt_ca_sample_interval', label: 'CA 采样间隔', unit: 's' },
  { key: 'adt_ca_sensitivity', label: 'CA 灵敏度', unit: 'A/V' },
];

function createRichStep(type: StepType = 'blank', idx = 0, solutions: string[] = []): RichStep {
  return {
    step_id: `step_${Date.now()}_${idx}`,
    step_type: type,
    notes: '',
    parallel_group: 0,
    pump_address: 1, pump_direction: 'FWD', pump_rpm: 120,
    volume_ul: 1000, transfer_duration: 30, transfer_duration_unit: 's',
    flush_channel_id: '', flush_rpm: 100, flush_cycle_duration_s: 30, flush_cycles: 1,
    duration_s: 60,
    prep_sol_params: {
      total_volume_ul: 100000,
      selected_solutions: Object.fromEntries(solutions.map((n, i) => [n, i < 2])),
      target_concentrations: Object.fromEntries(solutions.map((n) => [n, 0])),
      solvent_flags: Object.fromEntries(solutions.map((n, i) => [n, i === solutions.length - 1])),
      injection_order_numbers: Object.fromEntries(solutions.map((n, i) => [n, i + 1])),
      injection_order: solutions,
    },
    ec_settings: {
      technique: 'CV',
      e0: 0, eh: 0.8, el: -0.2, ef: 0,
      scan_rate: 0.05, sample_interval_ms: 100,
      sensitivity: undefined, autosensitivity: false,
      quiet_time_s: 2, seg_num: 2, scan_dir: 'FWD',
      run_time_s: 60,
      freq_low: 1, freq_high: 100000, amplitude: 0.005, bias_mode: 0,
      use_dummy_cell: false,
      adt_enabled: false, adt_num_cycles: 100,
      adt_cathodic_current_mA: -250, adt_cp_anodic_current_mA: 250,
      adt_cp_e_high: 2.0, adt_cp_e_low: -2.0,
      adt_cp_high_e_hold_time: 0, adt_cp_low_e_hold_time: 0,
      adt_cathodic_duration_s: 3.0, adt_cp_anodic_time_s: 3.0,
      adt_cp_polarity: 'n', adt_cp_sample_interval: 0.01,
      adt_cp_segments: 2, adt_cp_priority: 'time',
      adt_anodic_potential_V: 1.5, adt_ca_e_high: 1.5, adt_ca_e_low: -0.5,
      adt_ca_polarity: 'p', adt_ca_steps: 1,
      adt_anodic_duration_s: 2.0, adt_ca_sample_interval: 0.01,
      adt_ca_quiet_time: 0, adt_ca_sensitivity: 0.001,
      ir_compensation_enabled: false, ir_compensation_ohm: 0,
    },
  };
}

/** 将旧格式 {type, description, parameters} 兼容转换为 RichStep */
function toRichStep(raw: any, idx = 0): RichStep {
  if (raw && typeof raw.step_type === 'string') return raw as RichStep;
  const type: StepType = (raw?.step_type ?? raw?.type ?? 'blank') as StepType;
  const base = createRichStep(type, idx);
  return { ...base, step_type: type, notes: raw?.description ?? raw?.notes ?? '', parallel_group: raw?.parallel_group ?? 0, ...raw?.parameters };
}

// ─── NumField ────────────────────────────────────────────────────────────────

function NumField({ label, value, unit, onChange, min }: {
  label: string; value?: number; unit?: string;
  onChange: (v: number) => void; min?: number;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
      <div className="flex overflow-hidden rounded-lg border border-slate-300 bg-white focus-within:ring-2 focus-within:ring-blue-500">
        <input type="number" value={value ?? ''} min={min}
          onChange={(e) => onChange(Number(e.target.value))}
          className="min-w-0 flex-1 px-2 py-2 text-sm focus:outline-none" />
        {unit && <span className="flex items-center border-l border-slate-200 bg-slate-50 px-2 text-xs text-slate-500">{unit}</span>}
      </div>
    </label>
  );
}

// ─── EcField helper ─────────────────────────────────────────────────────────

function EcField({ fd, ec, onChange }: { fd: FD; ec: NonNullable<RichStep['ec_settings']>; onChange: (ec: NonNullable<RichStep['ec_settings']>) => void }) {
  const val = ec[fd.key as keyof typeof ec];
  if (fd.type === 'checkbox') {
    return (
      <label className="flex items-center gap-1.5 text-xs text-slate-700">
        <input type="checkbox" checked={!!val} onChange={(e) => onChange({ ...ec, [fd.key]: e.target.checked })} />
        <span>{fd.label}</span>
      </label>
    );
  }
  if (fd.type === 'select') {
    return (
      <label className="block">
        <span className="mb-0.5 block text-xs font-medium text-slate-600">{fd.label}</span>
        <select value={String(val ?? fd.options?.[0]?.value ?? '')}
          onChange={(e) => { const v = fd.key === 'bias_mode' ? Number(e.target.value) : e.target.value; onChange({ ...ec, [fd.key]: v }); }}
          className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-xs">
          {fd.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </label>
    );
  }
  return (
    <NumField key={fd.key} label={fd.label} unit={fd.unit} value={val as number | undefined}
      onChange={(v) => onChange({ ...ec, [fd.key]: v })} />
  );
}

// ─── StepForm — per-type form (now with cfg) ─────────────────────────────────

function StepForm({ step, onUpdate, cfg }: { step: RichStep; onUpdate: (s: RichStep) => void; cfg: SysCfg | null }) {
  const upd = (patch: Partial<RichStep>) => onUpdate({ ...step, ...patch });
  const solutions = useMemo(() => cfg?.dilution_channels?.map((c) => c.solution_name) ?? [], [cfg]);
  const dilMap = useMemo(() => {
    const m: Record<string, DilutionChannel> = {};
    for (const c of cfg?.dilution_channels ?? []) m[c.solution_name] = c;
    return m;
  }, [cfg]);
  const flushChs = cfg?.flush_channels ?? [];
  const pumps = cfg?.pumps ?? [];

  if (step.step_type === 'prep_sol') {
    const prep = step.prep_sol_params!;
    return (
      <div className="space-y-3">
        <NumField label="总体积" value={prep.total_volume_ul} unit="μL" min={0}
          onChange={(v) => upd({ prep_sol_params: { ...prep, total_volume_ul: v } })} />
        {solutions.length === 0 ? (
          <p className="text-xs text-amber-700">未检测到配液通道，请确认 MicroHySeeker 配置。</p>
        ) : (
          <div className="rounded-xl border border-slate-200 text-sm">
            <div className="grid grid-cols-[1fr,0.6fr,0.4fr,0.7fr,0.4fr,0.4fr] gap-1 border-b border-slate-200 bg-slate-50 px-2 py-1.5 text-xs font-semibold text-slate-500">
              <span>溶液</span><span>原浓度</span><span>泵</span><span>目标浓度</span><span>溶剂</span><span>顺序</span>
            </div>
            {solutions.map((sol) => {
              const ch = dilMap[sol];
              return (
                <div key={sol} className="grid grid-cols-[1fr,0.6fr,0.4fr,0.7fr,0.4fr,0.4fr] gap-1 items-center border-b border-slate-100 px-2 py-1.5 last:border-0">
                  <label className="flex items-center gap-1">
                    <input type="checkbox" checked={prep.selected_solutions[sol] ?? false}
                      onChange={(e) => upd({ prep_sol_params: { ...prep, selected_solutions: { ...prep.selected_solutions, [sol]: e.target.checked } } })} />
                    <span className="text-xs font-medium">{sol}</span>
                  </label>
                  <span className="text-xs text-slate-500">{ch?.stock_concentration ?? '—'}</span>
                  <span className="text-xs text-slate-500">{ch?.pump_address ?? '—'}</span>
                  <input type="number" step="0.001" value={prep.target_concentrations[sol] ?? 0}
                    onChange={(e) => upd({ prep_sol_params: { ...prep, target_concentrations: { ...prep.target_concentrations, [sol]: Number(e.target.value) } } })}
                    className="w-full rounded border border-slate-300 px-1 py-0.5 text-xs" />
                  <label className="flex items-center gap-0.5 text-xs">
                    <input type="checkbox" checked={prep.solvent_flags[sol] ?? false}
                      onChange={(e) => upd({ prep_sol_params: { ...prep, solvent_flags: { ...prep.solvent_flags, [sol]: e.target.checked } } })} />是
                  </label>
                  <input type="number" min={1} value={prep.injection_order_numbers[sol] ?? 1}
                    onChange={(e) => upd({ prep_sol_params: { ...prep, injection_order_numbers: { ...prep.injection_order_numbers, [sol]: Number(e.target.value) } } })}
                    className="w-full rounded border border-slate-300 px-1 py-0.5 text-xs" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  if (step.step_type === 'transfer' || step.step_type === 'evacuate') {
    return (
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="mb-0.5 block text-xs font-medium text-slate-600">泵地址</span>
          <select value={step.pump_address ?? 1} onChange={(e) => upd({ pump_address: Number(e.target.value) })}
            className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
            {pumps.length > 0
              ? pumps.map((p) => <option key={p.address} value={p.address}>{p.address} — {p.name}</option>)
              : Array.from({ length: 12 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
          </select>
        </label>
        <label className="block">
          <span className="mb-0.5 block text-xs font-medium text-slate-600">方向</span>
          <select value={step.pump_direction} onChange={(e) => upd({ pump_direction: e.target.value as 'FWD' | 'REV' })}
            className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
            <option value="FWD">FWD</option><option value="REV">REV</option>
          </select>
        </label>
        <NumField label="转速" value={step.pump_rpm} unit="RPM" min={0} onChange={(v) => upd({ pump_rpm: v })} />
        <NumField label="体积" value={step.volume_ul} unit="μL" min={0} onChange={(v) => upd({ volume_ul: v })} />
        <NumField label="持续时间" value={step.transfer_duration} min={0} onChange={(v) => upd({ transfer_duration: v })} />
        <label className="block">
          <span className="mb-0.5 block text-xs font-medium text-slate-600">时间单位</span>
          <select value={step.transfer_duration_unit} onChange={(e) => upd({ transfer_duration_unit: e.target.value as RichStep['transfer_duration_unit'] })}
            className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
            {['ms', 's', 'min', 'hr', 'cycle'].map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </label>
        {step.step_type === 'evacuate' && (
          <NumField label="排空次数" value={step.flush_cycles ?? 1} min={1} onChange={(v) => upd({ flush_cycles: v })} />
        )}
      </div>
    );
  }

  if (step.step_type === 'flush') {
    return (
      <div className="grid grid-cols-2 gap-3">
        <label className="col-span-2 block">
          <span className="mb-0.5 block text-xs font-medium text-slate-600">冲洗通道</span>
          {flushChs.length > 0 ? (
            <select value={step.flush_channel_id ?? ''} onChange={(e) => upd({ flush_channel_id: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
              <option value="">请选择通道</option>
              {flushChs.map((ch) => <option key={ch.channel_id} value={ch.channel_id}>{ch.pump_name} (泵{ch.pump_address}, {ch.work_type})</option>)}
            </select>
          ) : (
            <input type="text" value={step.flush_channel_id ?? ''} onChange={(e) => upd({ flush_channel_id: e.target.value })}
              className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm" placeholder="通道ID" />
          )}
        </label>
        <NumField label="转速" value={step.flush_rpm} unit="RPM" min={0} onChange={(v) => upd({ flush_rpm: v })} />
        <NumField label="单次时长" value={step.flush_cycle_duration_s} unit="s" min={0} onChange={(v) => upd({ flush_cycle_duration_s: v })} />
        <NumField label="循环次数" value={step.flush_cycles} min={1} onChange={(v) => upd({ flush_cycles: v })} />
      </div>
    );
  }

  if (step.step_type === 'echem') {
    const ec = step.ec_settings!;
    const techFields = TECHNIQUE_FIELDS[ec.technique] ?? [];
    const ecChange = (next: typeof ec) => upd({ ec_settings: next });
    return (
      <div className="space-y-3">
        <label className="block">
          <span className="mb-0.5 block text-xs font-medium text-slate-600">测量技术</span>
          <select value={ec.technique}
            onChange={(e) => ecChange({ ...ec, technique: e.target.value as EchemTechnique })}
            className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm">
            <option value="CV">CV — 循环伏安</option>
            <option value="LSV">LSV — 线性扫描</option>
            <option value="i-t">i-t — 计时电流</option>
            <option value="EIS">EIS — 交流阻抗</option>
            <option value="ADT">ADT — 加速耐久</option>
          </select>
        </label>
        <div className="grid grid-cols-2 gap-2">
          {techFields.map((fd) => <EcField key={fd.key} fd={fd} ec={ec} onChange={ecChange} />)}
        </div>
        {ec.technique === 'ADT' && (
          <>
            <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
              <h6 className="text-xs font-semibold text-indigo-800 mb-2">CP 计时电位法</h6>
              <div className="grid grid-cols-2 gap-2">
                {ADT_CP_FIELDS.map((fd) => <EcField key={fd.key} fd={fd} ec={ec} onChange={ecChange} />)}
              </div>
            </div>
            <div className="rounded-lg border border-teal-200 bg-teal-50 p-3">
              <h6 className="text-xs font-semibold text-teal-800 mb-2">CA 计时电流法</h6>
              <div className="grid grid-cols-2 gap-2">
                {ADT_CA_FIELDS.map((fd) => <EcField key={fd.key} fd={fd} ec={ec} onChange={ecChange} />)}
              </div>
            </div>
          </>
        )}
        {/* iR / dummy cell */}
        <div className="grid grid-cols-2 gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-700">
            <input type="checkbox" checked={!!ec.ir_compensation_enabled} onChange={(e) => ecChange({ ...ec, ir_compensation_enabled: e.target.checked })} />
            iR 补偿
          </label>
          {ec.ir_compensation_enabled && (
            <NumField label="补偿电阻" unit="Ω" value={ec.ir_compensation_ohm} onChange={(v) => ecChange({ ...ec, ir_compensation_ohm: v })} />
          )}
          <label className="flex items-center gap-1.5 text-xs text-slate-700">
            <input type="checkbox" checked={!!ec.use_dummy_cell} onChange={(e) => ecChange({ ...ec, use_dummy_cell: e.target.checked })} />
            Dummy Cell
          </label>
        </div>
      </div>
    );
  }

  if (step.step_type === 'blank') {
    return (
      <div className="space-y-3">
        <NumField label="等待时间" value={step.duration_s} unit="s" min={0} onChange={(v) => upd({ duration_s: v })} />
        <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-500">
          空白步骤：用于等待、观察或流程分段。
        </p>
      </div>
    );
  }

  return null;
}

// ─── Main export ─────────────────────────────────────────────────────────────

interface StepEditorProps {
  steps: any[];
  onChange: (steps: RichStep[]) => void;
}

export function StepEditor({ steps: rawSteps, onChange }: StepEditorProps) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [cfg, setCfg] = useState<SysCfg | null>(null);
  const [cfgLoading, setCfgLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const resp = await fetch('/api/system/config');
        if (resp.ok && !cancelled) setCfg(await resp.json());
      } catch { /* ignore */ }
      if (!cancelled) setCfgLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const solutions = useMemo(() => cfg?.dilution_channels?.map((c) => c.solution_name) ?? [], [cfg]);

  const steps: RichStep[] = rawSteps.map((s, i) => toRichStep(s, i));

  const emit = (next: RichStep[]) => onChange(next);

  const addStep = (type: StepType) => {
    const s = createRichStep(type, steps.length, solutions);
    emit([...steps, s]);
    setActiveId(s.step_id);
  };

  const removeStep = (id: string) => {
    const next = steps.filter((s) => s.step_id !== id);
    emit(next);
    if (activeId === id) setActiveId(next[0]?.step_id ?? null);
  };

  const updateStep = (updated: RichStep) => {
    emit(steps.map((s) => (s.step_id === updated.step_id ? updated : s)));
  };

  const moveStep = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[idx], next[target]] = [next[target], next[idx]];
    emit(next);
  };

  const activeStep = steps.find((s) => s.step_id === activeId) ?? null;

  if (cfgLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-sm text-slate-500">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />加载系统配置...
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-[1fr,1.1fr]">
      {/* ── 左：步骤列表 ── */}
      <div className="space-y-3">
        {/* 添加按钮 */}
        <div className="flex flex-wrap gap-1.5">
          {(['prep_sol', 'transfer', 'flush', 'echem', 'blank', 'evacuate'] as StepType[]).map((type) => (
            <button key={type} type="button" onClick={() => addStep(type)}
              className={`flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium transition hover:opacity-80 ${STEP_META[type].tone}`}>
              <Plus className="h-3 w-3" />{STEP_META[type].label}
            </button>
          ))}
        </div>

        {steps.length === 0 ? (
          <div className="rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 py-8 text-center text-sm text-slate-500">
            点击上方按钮添加步骤
          </div>
        ) : (
          <div className="space-y-2">
            {steps.map((step, idx) => {
              const meta = STEP_META[step.step_type];
              const Icon = meta.icon;
              const active = step.step_id === activeId;
              return (
                <div key={step.step_id}
                  className={`cursor-pointer rounded-xl border-l-4 border p-3 transition ${active ? 'border-l-blue-500 border-blue-300 bg-blue-50/40' : `${meta.leftBorder} border-slate-200 bg-white hover:bg-slate-50`}`}
                  onClick={() => setActiveId(step.step_id)}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 items-start gap-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white shadow-sm">
                        <Icon className="h-4 w-4 text-slate-700" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs font-semibold text-slate-800">Step {idx + 1}</span>
                          <span className={`rounded-full border px-1.5 py-0.5 text-xs font-medium ${meta.tone}`}>{meta.label}</span>
                          {(step.parallel_group ?? 0) > 0 && (
                            <span className="rounded-full border border-orange-200 bg-orange-50 px-1.5 py-0.5 text-xs font-medium text-orange-700">
                              ∥{step.parallel_group}
                            </span>
                          )}
                        </div>
                        {step.notes && <p className="mt-0.5 truncate text-xs text-slate-500">{step.notes}</p>}
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-0.5">
                      <button onClick={(e) => { e.stopPropagation(); moveStep(idx, -1); }} disabled={idx === 0}
                        className="rounded p-1 text-slate-400 hover:bg-white disabled:opacity-30" type="button">
                        <ArrowUp className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); moveStep(idx, 1); }} disabled={idx === steps.length - 1}
                        className="rounded p-1 text-slate-400 hover:bg-white disabled:opacity-30" type="button">
                        <ArrowDown className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); removeStep(step.step_id); }}
                        className="rounded p-1 text-red-400 hover:bg-red-50" type="button">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 右：步骤参数表单 ── */}
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        {activeStep ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${STEP_META[activeStep.step_type].tone}`}>
                {STEP_META[activeStep.step_type].label}
              </span>
              <label className="flex flex-1 items-center gap-2">
                <span className="shrink-0 text-xs font-medium text-slate-600">类型</span>
                <select value={activeStep.step_type}
                  onChange={(e) => updateStep({ ...activeStep, step_type: e.target.value as StepType })}
                  className="flex-1 rounded-lg border border-slate-300 px-2 py-1.5 text-xs">
                  {(Object.keys(STEP_META) as StepType[]).map((t) => <option key={t} value={t}>{STEP_META[t].label}</option>)}
                </select>
              </label>
            </div>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-600">备注</span>
              <textarea value={activeStep.notes}
                onChange={(e) => updateStep({ ...activeStep, notes: e.target.value })}
                rows={2}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="补充说明此步骤的目的或注意事项" />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs font-medium text-slate-600" title="0 = 串行执行；相同非零编号的步骤将同时执行">
                并行组 <span className="text-slate-400 font-normal">(0=串行)</span>
              </span>
              <input type="number" min={0} max={99} value={activeStep.parallel_group ?? 0}
                onChange={(e) => updateStep({ ...activeStep, parallel_group: Number(e.target.value) })}
                className="w-24 rounded-lg border border-slate-300 px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </label>
            <StepForm step={activeStep} onUpdate={updateStep} cfg={cfg} />
          </div>
        ) : (
          <div className="flex min-h-[120px] items-center justify-center text-sm text-slate-400">
            ← 点击左侧步骤卡片开始编辑
          </div>
        )}
      </div>
    </div>
  );
}
