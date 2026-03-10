import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Play, CheckCircle, Clock, AlertCircle } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
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

const STATUS_CONFIG: Record<string, { icon: ReactNode; label: string; color: string }> = {
  created: {
    icon: <Clock className="h-5 w-5" />,
    label: '已创建',
    color: 'text-gray-600 bg-gray-100',
  },
  running: {
    icon: <Play className="h-5 w-5 animate-pulse" />,
    label: '运行中',
    color: 'text-blue-600 bg-blue-100',
  },
  completed: {
    icon: <CheckCircle className="h-5 w-5" />,
    label: '已完成',
    color: 'text-green-600 bg-green-100',
  },
  failed: {
    icon: <AlertCircle className="h-5 w-5" />,
    label: '失败',
    color: 'text-red-600 bg-red-100',
  },
};

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
      alert('实验已开始执行！');
    } catch (err) {
      alert(err instanceof Error ? err.message : '执行失败');
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error || !experiment) {
    return (
      <div className="p-6">
        <div className="text-red-600 bg-red-50 p-4 rounded-lg">
          {error || '实验不存在'}
        </div>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 flex items-center gap-2 text-blue-600"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
      </div>
    );
  }

  const statusConf = STATUS_CONFIG[experiment.status] ?? STATUS_CONFIG.created;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-2"
          >
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <h2 className="text-2xl font-bold text-gray-900">{experiment.name}</h2>
          {experiment.description && (
            <p className="text-gray-600 mt-1">{experiment.description}</p>
          )}
          <div className="flex items-center gap-3 mt-2">
            <span
              className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${statusConf.color}`}
            >
              {statusConf.icon}
              {statusConf.label}
            </span>
            {experiment.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        {experiment.status === 'created' && (
          <button
            onClick={handleExecute}
            disabled={executing}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            <Play className="h-4 w-4" />
            {executing ? '提交中...' : '执行实验'}
          </button>
        )}
      </div>

      {/* Metadata */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-3">实验信息</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-gray-500">实验 ID</p>
            <p className="font-mono text-xs mt-0.5 text-gray-800">{experiment.exp_id}</p>
          </div>
          <div>
            <p className="text-gray-500">创建时间</p>
            <p className="mt-0.5 text-gray-800">
              {new Date(experiment.created_at).toLocaleString('zh-CN')}
            </p>
          </div>
          {experiment.started_at && (
            <div>
              <p className="text-gray-500">开始时间</p>
              <p className="mt-0.5 text-gray-800">
                {new Date(experiment.started_at).toLocaleString('zh-CN')}
              </p>
            </div>
          )}
          {experiment.completed_at && (
            <div>
              <p className="text-gray-500">完成时间</p>
              <p className="mt-0.5 text-gray-800">
                {new Date(experiment.completed_at).toLocaleString('zh-CN')}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Steps */}
      {experiment.steps.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-3">实验步骤</h3>
          <div className="space-y-2">
            {experiment.steps.map((step, i) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <span className="w-6 h-6 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold">
                  {i + 1}
                </span>
                <span className="uppercase text-xs font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                  {step.step_type}
                </span>
                <span className="text-sm text-gray-700">
                  {step.description || `步骤 ${i + 1}`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">实验数据</h3>
        {experiment.data.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={experiment.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="x" label={{ value: 'E / V', position: 'insideBottomRight', offset: -5 }} />
              <YAxis label={{ value: 'I / A', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Line type="monotone" dataKey="y" stroke="#3B82F6" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-32 flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
            暂无数据
            {experiment.status === 'created' && ' — 请先执行实验'}
          </div>
        )}
      </div>
    </div>
  );
}
