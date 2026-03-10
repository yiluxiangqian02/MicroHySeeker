import { useState, useEffect } from 'react';
import { X, Search, Calendar, Layers, ChevronRight } from 'lucide-react';

interface Experiment {
  exp_id: string;
  name: string;
  description: string;
  steps: any[];
  status: string;
  created_at: string;
  tags?: string[];
}

interface ExperimentSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (experiment: Experiment) => void;
}

export default function ExperimentSelector({ isOpen, onClose, onSelect }: ExperimentSelectorProps) {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadExperiments();
    }
  }, [isOpen]);

  const loadExperiments = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8200/api/experiments/recent?limit=20');
      const data = await response.json();
      setExperiments(data.experiments || []);
    } catch (error) {
      console.error('Failed to load experiments:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredExperiments = experiments.filter(exp =>
    exp.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    exp.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleSelect = () => {
    if (selectedExp) {
      onSelect(selectedExp);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-[900px] h-[600px] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">选择实验</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索实验名称或描述..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Experiment List */}
          <div className="w-1/2 border-r border-gray-200 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                  <p>加载中...</p>
                </div>
              </div>
            ) : filteredExperiments.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>没有找到实验</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {filteredExperiments.map((exp) => (
                  <div
                    key={exp.exp_id}
                    onClick={() => setSelectedExp(exp)}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedExp?.exp_id === exp.exp_id
                        ? 'bg-blue-50 border-l-4 border-blue-500'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900">{exp.name}</h3>
                        <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                          {exp.description || '无描述'}
                        </p>
                        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                          <div className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {formatDate(exp.created_at)}
                          </div>
                          <div className="flex items-center gap-1">
                            <Layers className="w-3 h-3" />
                            {exp.steps.length} 步骤
                          </div>
                        </div>
                        {exp.tags && exp.tags.length > 0 && (
                          <div className="flex gap-1 mt-2">
                            {exp.tags.map((tag, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0 ml-2" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Preview Panel */}
          <div className="w-1/2 overflow-y-auto bg-gray-50">
            {selectedExp ? (
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">实验详情</h3>

                <div className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700">实验名称</label>
                    <p className="mt-1 text-gray-900">{selectedExp.name}</p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-700">描述</label>
                    <p className="mt-1 text-gray-600">{selectedExp.description || '无描述'}</p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-700">状态</label>
                    <p className="mt-1">
                      <span
                        className={`px-2 py-1 rounded text-sm ${
                          selectedExp.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : selectedExp.status === 'running'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {selectedExp.status === 'completed' && '已完成'}
                        {selectedExp.status === 'running' && '运行中'}
                        {selectedExp.status === 'created' && '已创建'}
                      </span>
                    </p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-700">创建时间</label>
                    <p className="mt-1 text-gray-600">{formatDate(selectedExp.created_at)}</p>
                  </div>

                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-2 block">
                      实验步骤 ({selectedExp.steps.length})
                    </label>
                    <div className="space-y-2">
                      {selectedExp.steps.map((step, idx) => (
                        <div
                          key={idx}
                          className="bg-white p-3 rounded-lg border border-gray-200"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-medium text-gray-500">
                              步骤 {idx + 1}
                            </span>
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
                              {step.step_type?.toUpperCase() || 'UNKNOWN'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700">
                            {step.description || '无描述'}
                          </p>
                          {step.params && Object.keys(step.params).length > 0 && (
                            <div className="mt-2 text-xs text-gray-500">
                              {Object.entries(step.params).slice(0, 3).map(([key, value]) => (
                                <div key={key}>
                                  {key}: {String(value)}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>选择一个实验查看详情</p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSelect}
            disabled={!selectedExp}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            加载实验
          </button>
        </div>
      </div>
    </div>
  );
}
