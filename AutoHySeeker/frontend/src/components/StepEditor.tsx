import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react';

interface Step {
  type: string;
  description: string;
  parameters: Record<string, any>;
}

interface StepEditorProps {
  steps: Step[];
  onChange: (steps: Step[]) => void;
}

const STEP_TYPES = [
  'cv',
  'lsv',
  'eis',
  'prep_sol',
  'flush',
  'transfer',
  'blank',
  'evacuate',
];

export function StepEditor({ steps, onChange }: StepEditorProps) {
  const { t } = useTranslation();
  const [expandedStep, setExpandedStep] = useState<number | null>(null);

  const addStep = () => {
    onChange([
      ...steps,
      { type: 'cv', description: '', parameters: {} },
    ]);
    setExpandedStep(steps.length);
  };

  const removeStep = (index: number) => {
    onChange(steps.filter((_, i) => i !== index));
    if (expandedStep === index) setExpandedStep(null);
  };

  const updateStep = (index: number, field: keyof Step, value: any) => {
    const newSteps = [...steps];
    newSteps[index] = { ...newSteps[index], [field]: value };
    onChange(newSteps);
  };

  const moveStep = (index: number, direction: 'up' | 'down') => {
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === steps.length - 1)
    ) {
      return;
    }

    const newSteps = [...steps];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    [newSteps[index], newSteps[targetIndex]] = [newSteps[targetIndex], newSteps[index]];
    onChange(newSteps);
    setExpandedStep(targetIndex);
  };

  return (
    <div className="space-y-3">
      {steps.length === 0 ? (
        <div className="text-center py-8 bg-slate-50 rounded-lg border-2 border-dashed border-slate-300">
          <p className="text-gray-500 mb-4">{t('templates.noSteps')}</p>
          <button onClick={addStep} className="btn-primary">
            <Plus className="h-4 w-4 inline mr-2" />
            {t('templates.addStep')}
          </button>
        </div>
      ) : (
        <>
          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="border border-slate-200 rounded-lg overflow-hidden"
            >
              {/* Step Header */}
              <div className="flex items-center justify-between p-4 bg-slate-50">
                <div className="flex items-center space-x-3">
                  <span className="flex items-center justify-center w-8 h-8 bg-blue-600 text-white rounded-full text-sm font-semibold">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-medium">{step.type}</p>
                    {step.description && (
                      <p className="text-sm text-gray-600">{step.description}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => moveStep(index, 'up')}
                    disabled={index === 0}
                    className="p-1 hover:bg-slate-200 rounded disabled:opacity-30"
                  >
                    <ChevronUp className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() => moveStep(index, 'down')}
                    disabled={index === steps.length - 1}
                    className="p-1 hover:bg-slate-200 rounded disabled:opacity-30"
                  >
                    <ChevronDown className="h-4 w-4" />
                  </button>
                  <button
                    onClick={() =>
                      setExpandedStep(expandedStep === index ? null : index)
                    }
                    className="px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    {expandedStep === index ? t('common.collapse') : t('common.expand')}
                  </button>
                  <button
                    onClick={() => removeStep(index)}
                    className="p-1 hover:bg-red-100 rounded text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Step Details */}
              {expandedStep === index && (
                <div className="p-4 space-y-4 bg-white">
                  {/* Step Type */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('templates.stepType')}
                    </label>
                    <select
                      value={step.type}
                      onChange={(e) => updateStep(index, 'type', e.target.value)}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {STEP_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('templates.stepDescription')}
                    </label>
                    <input
                      type="text"
                      value={step.description}
                      onChange={(e) =>
                        updateStep(index, 'description', e.target.value)
                      }
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder={t('templates.stepDescriptionPlaceholder')}
                    />
                  </div>

                  {/* Parameters */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('templates.parameters')}
                    </label>
                    <textarea
                      value={JSON.stringify(step.parameters, null, 2)}
                      onChange={(e) => {
                        try {
                          const params = JSON.parse(e.target.value);
                          updateStep(index, 'parameters', params);
                        } catch (error) {
                          // Invalid JSON, don't update
                        }
                      }}
                      rows={6}
                      className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      placeholder="{}"
                    />
                  </div>
                </div>
              )}
            </motion.div>
          ))}

          <button onClick={addStep} className="w-full btn-secondary">
            <Plus className="h-4 w-4 inline mr-2" />
            {t('templates.addStep')}
          </button>
        </>
      )}
    </div>
  );
}
