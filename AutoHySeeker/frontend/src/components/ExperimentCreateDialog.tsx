import { useState, useCallback } from 'react';
import { Plus, X, Trash2, ChevronDown, ChevronRight, Clock } from 'lucide-react';

// ── Parameter metadata ────────────────────────────────────────────────────────

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
  params: ParamDef[];
  /** Estimate experiment duration in seconds given params */
  estimateSec: (params: Record<string, number>) => number;
}

const STEP_TYPES: Record<string, StepTypeDef> = {
  cv: {
    label: 'CV – 循环伏安法',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V',  min: -10,  max: 10,     step: 0.1,   defaultValue: 0 },
      { key: 'endVoltage',   label: '终止电压', unit: 'V',  min: -10,  max: 10,     step: 0.1,   defaultValue: 1 },
      { key: 'scanRate',     label: '扫描速率', unit: 'mV/s', min: 1,  max: 10000,  step: 1,     defaultValue: 50 },
      { key: 'cycles',       label: '循环次数', unit: '次',  min: 1,    max: 100,    step: 1,     defaultValue: 1 },
      { key: 'stepVoltage',  label: '步进电压', unit: 'mV', min: 0.1,  max: 100,    step: 0.1,   defaultValue: 5,   advanced: true },
      { key: 'quietTime',    label: '静置时间', unit: 's',  min: 0,    max: 3600,   step: 1,     defaultValue: 2,   advanced: true },
      { key: 'sensitivity',  label: '灵敏度',   unit: 'μA', min: 1,    max: 1000,   step: 1,     defaultValue: 100, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 1) - (p.startVoltage ?? 0)) * 1000; // mV
      const rate = p.scanRate ?? 50;
      return Math.round((range / rate) * 2 * (p.cycles ?? 1) + (p.quietTime ?? 2));
    },
  },
  eis: {
    label: 'EIS – 电化学阻抗谱',
    params: [
      { key: 'startFreq',      label: '起始频率', unit: 'Hz', min: 0.01, max: 1e6,  step: 1,   defaultValue: 100000 },
      { key: 'endFreq',        label: '终止频率', unit: 'Hz', min: 0.01, max: 1e6,  step: 0.01, defaultValue: 0.1 },
      { key: 'amplitude',      label: '振幅',     unit: 'mV', min: 1,    max: 100,  step: 1,   defaultValue: 10 },
      { key: 'dcVoltage',      label: '直流偏压', unit: 'V',  min: -10,  max: 10,   step: 0.1, defaultValue: 0 },
      { key: 'pointsPerDecade',label: '每十倍频点数', unit: '点', min: 5, max: 20, step: 1, defaultValue: 10, advanced: true },
      { key: 'integrationTime',label: '积分时间', unit: 's',  min: 0.1,  max: 10,   step: 0.1, defaultValue: 1, advanced: true },
    ],
    estimateSec: (p) => {
      const decades = Math.log10((p.startFreq ?? 1e5) / Math.max(p.endFreq ?? 0.1, 0.001));
      const pts = decades * (p.pointsPerDecade ?? 10);
      return Math.round(pts * (p.integrationTime ?? 1) * 2);
    },
  },
  ca: {
    label: 'CA – 计时电流法',
    params: [
      { key: 'voltage',        label: '电压',     unit: 'V',  min: -10, max: 10,   step: 0.1,  defaultValue: 0.5 },
      { key: 'duration',       label: '持续时间', unit: 's',  min: 1,   max: 36000,step: 1,    defaultValue: 60 },
      { key: 'sampleInterval', label: '采样间隔', unit: 's',  min: 0.01,max: 60,   step: 0.01, defaultValue: 0.1 },
      { key: 'quietTime',      label: '静置时间', unit: 's',  min: 0,   max: 3600, step: 1,    defaultValue: 2, advanced: true },
      { key: 'sensitivity',    label: '灵敏度',   unit: 'μA', min: 1,   max: 1000, step: 1,    defaultValue: 100, advanced: true },
    ],
    estimateSec: (p) => (p.duration ?? 60) + (p.quietTime ?? 2),
  },
  cp: {
    label: 'CP – 计时电位法',
    params: [
      { key: 'current',        label: '电流',     unit: 'mA', min: -1000, max: 1000, step: 0.1,  defaultValue: 1 },
      { key: 'duration',       label: '持续时间', unit: 's',  min: 1,     max: 36000,step: 1,    defaultValue: 60 },
      { key: 'sampleInterval', label: '采样间隔', unit: 's',  min: 0.01,  max: 60,   step: 0.01, defaultValue: 0.1 },
      { key: 'quietTime',      label: '静置时间', unit: 's',  min: 0,     max: 3600, step: 1,    defaultValue: 2, advanced: true },
    ],
    estimateSec: (p) => (p.duration ?? 60) + (p.quietTime ?? 2),
  },
  lsv: {
    label: 'LSV – 线性扫描伏安法',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V',   min: -10, max: 10,    step: 0.1, defaultValue: 0 },
      { key: 'endVoltage',   label: '终止电压', unit: 'V',   min: -10, max: 10,    step: 0.1, defaultValue: 1 },
      { key: 'scanRate',     label: '扫描速率', unit: 'mV/s',min: 1,   max: 10000, step: 1,   defaultValue: 50 },
      { key: 'stepVoltage',  label: '步进电压', unit: 'mV',  min: 0.1, max: 100,   step: 0.1, defaultValue: 5, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 1) - (p.startVoltage ?? 0)) * 1000;
      return Math.round(range / (p.scanRate ?? 50));
    },
  },
  dpv: {
    label: 'DPV – 差分脉冲伏安法',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V',   min: -10, max: 10,   step: 0.1, defaultValue: -0.5 },
      { key: 'endVoltage',   label: '终止电压', unit: 'V',   min: -10, max: 10,   step: 0.1, defaultValue: 0.5 },
      { key: 'pulseAmplitude',label: '脉冲幅度',unit: 'mV',  min: 1,   max: 250,  step: 1,   defaultValue: 50 },
      { key: 'pulseWidth',   label: '脉冲宽度', unit: 'ms',  min: 1,   max: 1000, step: 1,   defaultValue: 50, advanced: true },
      { key: 'scanRate',     label: '扫描速率', unit: 'mV/s',min: 1,   max: 1000, step: 1,   defaultValue: 5, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 0.5) - (p.startVoltage ?? -0.5)) * 1000;
      return Math.round(range / (p.scanRate ?? 5));
    },
  },
  sqv: {
    label: 'SWV – 方波伏安法',
    params: [
      { key: 'startVoltage', label: '起始电压', unit: 'V',   min: -10, max: 10,   step: 0.1, defaultValue: -0.5 },
      { key: 'endVoltage',   label: '终止电压', unit: 'V',   min: -10, max: 10,   step: 0.1, defaultValue: 0.5 },
      { key: 'frequency',    label: '频率',     unit: 'Hz',  min: 1,   max: 1000, step: 1,   defaultValue: 15 },
      { key: 'amplitude',    label: '幅度',     unit: 'mV',  min: 1,   max: 250,  step: 1,   defaultValue: 25, advanced: true },
      { key: 'increment',    label: '电位增量', unit: 'mV',  min: 0.1, max: 10,   step: 0.1, defaultValue: 2, advanced: true },
    ],
    estimateSec: (p) => {
      const range = Math.abs((p.endVoltage ?? 0.5) - (p.startVoltage ?? -0.5)) * 1000;
      const inc = p.increment ?? 2;
      return Math.round((range / inc) / (p.frequency ?? 15));
    },
  },
};

// ── Step state ────────────────────────────────────────────────────────────────

interface StepState {
  step_type: string;
  description: string;
  params: Record<string, number>;
  showAdvanced: boolean;
}

function buildDefaultParams(stepType: string): Record<string, number> {
  const def = STEP_TYPES[stepType];
  if (!def) return {};
  return Object.fromEntries(def.params.map((p) => [p.key, p.defaultValue]));
}

function formatDuration(sec: number): string {
  if (sec < 60) return `${sec} 秒`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s > 0 ? `${m} 分 ${s} 秒` : `${m} 分钟`;
}

// ── Number input with unit badge ──────────────────────────────────────────────

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
    if (isNaN(n)) {
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
    onChange(def.key, n);
  };

  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 mb-1">
        {def.label}
        {def.hint && <span className="ml-1 text-gray-400 font-normal">({def.hint})</span>}
      </label>
      <div className={`flex items-stretch border rounded-lg overflow-hidden ${error ? 'border-red-400' : 'border-gray-300'} focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent`}>
        <input
          type="number"
          value={raw}
          min={def.min}
          max={def.max}
          step={def.step}
          onChange={(e) => setRaw(e.target.value)}
          onBlur={handleBlur}
          className="flex-1 px-3 py-2 text-sm focus:outline-none bg-white"
          placeholder={String(def.defaultValue)}
        />
        <span className="flex items-center px-2 bg-gray-50 border-l border-gray-300 text-xs text-gray-500 whitespace-nowrap">
          {def.unit}
        </span>
      </div>
      {error && <p className="mt-0.5 text-xs text-red-500">{error}</p>}
      <p className="mt-0.5 text-xs text-gray-400">范围: {def.min} ~ {def.max} {def.unit}</p>
    </div>
  );
}

// ── Step editor ───────────────────────────────────────────────────────────────

interface StepEditorCardProps {
  index: number;
  step: StepState;
  onChange: (index: number, next: StepState) => void;
  onRemove: (index: number) => void;
}

function StepEditorCard({ index, step, onChange, onRemove }: StepEditorCardProps) {
  const typeDef = STEP_TYPES[step.step_type];
  const basicParams = typeDef?.params.filter((p) => !p.advanced) ?? [];
  const advancedParams = typeDef?.params.filter((p) => p.advanced) ?? [];

  const handleTypeChange = (newType: string) => {
    onChange(index, {
      ...step,
      step_type: newType,
      params: buildDefaultParams(newType),
    });
  };

  const handleParamChange = (key: string, val: number) => {
    onChange(index, { ...step, params: { ...step.params, [key]: val } });
  };

  const estimatedSec = typeDef?.estimateSec(step.params) ?? 0;

  return (
    <div className="border border-gray-200 rounded-xl p-4 bg-gray-50 space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
          {index + 1}
        </span>
        <div className="flex-1 grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">步骤类型</label>
            <select
              value={step.step_type}
              onChange={(e) => handleTypeChange(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(STEP_TYPES).map(([key, def]) => (
                <option key={key} value={key}>{def.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">描述（可选）</label>
            <input
              type="text"
              value={step.description}
              onChange={(e) => onChange(index, { ...step, description: e.target.value })}
              placeholder={`步骤 ${index + 1} 描述`}
              className="w-full border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <button
          onClick={() => onRemove(index)}
          className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors p-1"
          title="删除步骤"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Basic params */}
      {basicParams.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">基础参数</p>
          <div className="grid grid-cols-2 gap-3">
            {basicParams.map((p) => (
              <NumInput
                key={p.key}
                def={p}
                value={step.params[p.key] ?? p.defaultValue}
                onChange={handleParamChange}
              />
            ))}
          </div>
        </div>
      )}

      {/* Advanced params (collapsible) */}
      {advancedParams.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => onChange(index, { ...step, showAdvanced: !step.showAdvanced })}
            className="flex items-center gap-1 text-xs font-semibold text-gray-500 hover:text-gray-700 transition-colors"
          >
            {step.showAdvanced ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            高级参数
          </button>
          {step.showAdvanced && (
            <div className="mt-2 grid grid-cols-2 gap-3">
              {advancedParams.map((p) => (
                <NumInput
                  key={p.key}
                  def={p}
                  value={step.params[p.key] ?? p.defaultValue}
                  onChange={handleParamChange}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Estimated time badge */}
      {estimatedSec > 0 && (
        <div className="flex items-center gap-1.5 text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-1.5">
          <Clock className="h-3.5 w-3.5" />
          <span>预估时长: <strong>{formatDuration(estimatedSec)}</strong></span>
        </div>
      )}
    </div>
  );
}

// ── Dialog ────────────────────────────────────────────────────────────────────

interface ExperimentCreateDialogProps {
  onClose: () => void;
  onSubmit: (experiment: Record<string, unknown>) => void;
}

export function ExperimentCreateDialog({ onClose, onSubmit }: ExperimentCreateDialogProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [steps, setSteps] = useState<StepState[]>([]);
  const [tags, setTags] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const addStep = useCallback(() => {
    setSteps((prev) => [
      ...prev,
      { step_type: 'cv', description: '', params: buildDefaultParams('cv'), showAdvanced: false },
    ]);
  }, []);

  const removeStep = useCallback((index: number) => {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateStep = useCallback((index: number, next: StepState) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? next : s)));
  }, []);

  const totalEstimatedSec = steps.reduce((acc, step) => {
    const def = STEP_TYPES[step.step_type];
    return acc + (def?.estimateSec(step.params) ?? 0);
  }, 0);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError('请输入实验名称');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        name: name.trim(),
        description: description.trim(),
        steps: steps.map(({ step_type, description: desc, params }) => ({
          step_type,
          description: desc,
          params: Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)])),
        })),
        tags: tags.split(',').map((t) => t.trim()).filter(Boolean),
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-gray-900">创建实验</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X className="h-6 w-6" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {/* Basic info */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              实验名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              placeholder="输入实验名称..."
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              placeholder="实验描述（可选）..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
            <input
              type="text"
              placeholder="例如: CV, 电化学, 基线"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Steps */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">
                实验步骤 <span className="text-gray-400 font-normal">({steps.length} 步)</span>
              </label>
              <button
                onClick={addStep}
                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                <Plus className="h-4 w-4" />
                添加步骤
              </button>
            </div>

            {steps.length === 0 ? (
              <div
                onClick={addStep}
                className="cursor-pointer text-center py-8 border-2 border-dashed border-gray-200 rounded-xl text-gray-400 text-sm hover:border-blue-300 hover:text-blue-400 transition-colors"
              >
                <Plus className="h-6 w-6 mx-auto mb-1 opacity-60" />
                点击添加第一个实验步骤
              </div>
            ) : (
              <div className="space-y-3">
                {steps.map((step, index) => (
                  <StepEditorCard
                    key={index}
                    index={index}
                    step={step}
                    onChange={updateStep}
                    onRemove={removeStep}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Total estimated time */}
          {totalEstimatedSec > 0 && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-100 rounded-lg text-sm text-blue-700">
              <Clock className="h-4 w-4 flex-shrink-0" />
              <span>
                预估总实验时间：<strong>{formatDuration(totalEstimatedSec)}</strong>
                （{steps.length} 个步骤）
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 mt-6 pt-4 border-t border-gray-200">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg font-medium transition-colors text-sm"
          >
            {submitting ? '创建中...' : '创建实验'}
          </button>
          <button
            onClick={onClose}
            disabled={submitting}
            className="flex-1 border border-gray-300 hover:bg-gray-50 px-4 py-2 rounded-lg font-medium transition-colors text-sm"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
