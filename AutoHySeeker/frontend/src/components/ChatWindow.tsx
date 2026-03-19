import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock3,
  Database,
  FlaskConical,
  History,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
  Trash2,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  agent_type?: string;
  meta?: {
    mode?: 'live' | 'fallback';
    statusLabel?: string;
  };
}

interface ExperimentContextSummary {
  experimentName: string;
  stage: string;
  objective: string;
  latestObservation: string;
  nextSuggestion: string;
}

interface ChatWindowProps {
  isOpen?: boolean;
  onClose?: () => void;
  mode?: 'drawer' | 'embedded';
  title?: string;
  subtitle?: string;
  contextItems?: string[];
  experimentContext?: Partial<ExperimentContextSummary>;
}

type ConnectionState = 'connecting' | 'live' | 'fallback' | 'error';

const STORAGE_KEY = 'autohyseeker.knowledge-chat.history';

const defaultExperimentContext: ExperimentContextSummary = {
  experimentName: '当前实验上下文未接入',
  stage: '待补充当前 step / run 状态',
  objective: '这里后续会显示本轮实验目标、关键参数和约束条件。',
  latestObservation: '尚未收到实时实验摘要，当前用产品级占位信息承接。',
  nextSuggestion: '可以先围绕 technique、异常、历史实验和下一轮修改方向提问。',
};

const quickActions = [
  { label: '问当前实验', question: '结合当前实验上下文，这一轮最值得优先关注哪个 step？' },
  { label: '问知识库', question: 'CV 实验的扫描速率通常怎么选？' },
  { label: '问运行异常', question: '如果 transfer 步骤卡住，最常见的原因和排查顺序是什么？' },
  { label: '问历史经验', question: '最近做过哪些和 EIS 相关的实验，结果大概怎样？' },
];

function createWelcomeMessage(): ChatMessage {
  return {
    id: 'welcome_knowledge_chat',
    role: 'assistant',
    content: [
      '这里是知识管理 / 知识库 Chat。',
      '我不是普通闲聊框，而是围绕实验设计、知识库文档、历史实验和运行异常服务的实验助手入口。',
      '你可以直接问：当前 step 为什么这么设计、某个 technique 怎么选、最近相似 run 有什么经验、下一轮优先改什么变量。',
    ].join('\n'),
    timestamp: new Date().toISOString(),
    agent_type: 'knowledge_manager',
    meta: {
      mode: 'fallback',
      statusLabel: 'welcome',
    },
  };
}

function readLocalMessages(): ChatMessage[] {
  if (typeof window === 'undefined') return [];

  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveLocalMessages(messages: ChatMessage[]) {
  if (typeof window === 'undefined') return;
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-60)));
}

function buildFallbackAnswer(question: string): ChatMessage {
  const lowered = question.toLowerCase();
  let content = [
    '后端知识检索当前不可用，我先用 fallback knowledge flow 托住这次对话。',
    '我会把你的问题按“知识库 / 历史实验 / 方法经验 / 实验上下文”来组织回答。',
    '真实 retrieval 接入后，这里会补上来源引用、相似实验和更明确的执行建议。',
  ].join('\n');

  if (lowered.includes('cv') || lowered.includes('lsv') || lowered.includes('eis') || lowered.includes('dpv') || lowered.includes('扫描速率')) {
    content = [
      'fallback 结果：你问的是电化学 technique / 参数选择。',
      '• 如果是首次摸底，建议先从 CV 开始，快速判断氧化还原行为和窗口范围。',
      '• 如果你关心界面过程或电荷转移，再补 EIS。',
      '• 扫描速率通常先从 50 mV/s 起步；若信号弱或想看细节，再降到 10–20 mV/s。',
      '• 下一步最好补充样品类型、目标信号和最近一次成功实验。',
    ].join('\n');
  } else if (lowered.includes('transfer') || lowered.includes('flush') || lowered.includes('evacuate') || lowered.includes('卡住')) {
    content = [
      'fallback 结果：你问的是实验流程执行异常。',
      '建议优先检查：',
      '1. 泵地址 / 方向 / 通道映射是否正确；',
      '2. RPM、体积模式、时长模式是否和当前 step 一致；',
      '3. 当前 run 是否被前一个 step 占住资源；',
      '4. 最近日志里是否出现 timeout、busy、connection reset。',
      '如果你愿意，下一条可以直接贴 step 参数，我按“排查顺序”继续拆。',
    ].join('\n');
  } else if (lowered.includes('下一轮') || lowered.includes('建议') || lowered.includes('优化') || lowered.includes('改哪个')) {
    content = [
      'fallback 结果：你在问下一轮实验设计。',
      '建议先只改一个变量，避免把结论搅浑。',
      '推荐优先级：',
      '1. technique 核心参数（如扫描速率 / 电位范围）；',
      '2. transfer / flush 等执行条件；',
      '3. 配方或样品预处理。',
      '如果后续接入真实 agent，这里会返回结构化建议卡和历史 run 对比。',
    ].join('\n');
  } else if (lowered.includes('历史') || lowered.includes('run') || lowered.includes('相似实验')) {
    content = [
      'fallback 结果：你在问历史实验经验。',
      '当前前端先给出产品级占位：后续这里会展示相似实验列表、关键参数、结果摘要和失败原因。',
      '现在建议你继续补充：目标 analyte、technique、异常现象、你最关心的判断维度。',
    ].join('\n');
  }

  return {
    id: `fallback_${Date.now()}`,
    role: 'assistant',
    content,
    timestamp: new Date().toISOString(),
    agent_type: 'knowledge_manager',
    meta: {
      mode: 'fallback',
      statusLabel: 'fallback',
    },
  };
}

function normalizeMessages(messages: ChatMessage[]): ChatMessage[] {
  return messages.map((message, index) => ({
    ...message,
    id: message.id || `msg_${index}_${Date.now()}`,
    meta: message.meta ?? (message.role === 'assistant' ? { mode: 'live', statusLabel: 'live' } : undefined),
  }));
}

function getAgentLabel(message: ChatMessage) {
  if (message.agent_type === 'data_analyst') return '📊 数据分析助手';
  if (message.agent_type === 'experiment_designer') return '🧪 方案设计助手';
  if (message.agent_type === 'knowledge_manager') return '📚 知识管理 / 知识库 Chat';
  return message.role === 'user' ? '👤 用户提问' : '🤖 助手回复';
}

export default function ChatWindow({
  isOpen = true,
  onClose,
  mode = 'drawer',
  title = '知识管理 / 知识库 Chat',
  subtitle = '围绕实验上下文、知识库文档、历史实验和方案经验提问；即使后端暂时不可用，前端也保持可聊、可看、可演示。',
  contextItems = ['知识库 / 方法文档', '历史实验 / 相似 run', '方案设计建议 / 失败复盘'],
  experimentContext,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isBootstrapped, setIsBootstrapped] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [statusText, setStatusText] = useState('正在连接知识管理服务...');
  const [lastError, setLastError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const mergedExperimentContext = {
    ...defaultExperimentContext,
    ...experimentContext,
  };

  const shellClass =
    mode === 'embedded'
      ? 'flex h-full min-h-[760px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm'
      : 'fixed bottom-4 right-4 z-50 flex h-[760px] w-[480px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl';

  useEffect(() => {
    if (containerRef.current) {
        containerRef.current.scrollTo({
            top: containerRef.current.scrollHeight,
            behavior: 'smooth'
        });
    }
  }, [messages, isLoading]);

  useEffect(() => {
    if (!isOpen || isBootstrapped) return;
    void bootstrapHistory();
  }, [isOpen, isBootstrapped]);

  useEffect(() => {
    if (!messages.length) return;
    saveLocalMessages(messages);
  }, [messages]);

  const bootstrapHistory = async () => {
    setConnectionState('connecting');
    setStatusText('正在连接知识管理服务...');
    setLastError(null);

    const localMessages = readLocalMessages();

    try {
      const response = await fetch('/api/v1/chat/history?limit=50');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const remoteMessages = Array.isArray(data.messages) ? normalizeMessages(data.messages) : [];
      const nextMessages = remoteMessages.length > 0 ? remoteMessages : localMessages.length > 0 ? localMessages : [createWelcomeMessage()];

      setMessages(nextMessages);
      setConnectionState('live');
      setStatusText(remoteMessages.length > 0 ? '已连接后端，历史消息已恢复。' : '已连接后端，当前还没有历史消息。');
      setIsBootstrapped(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误';
      setMessages(localMessages.length > 0 ? localMessages : [createWelcomeMessage()]);
      setConnectionState(localMessages.length > 0 ? 'fallback' : 'error');
      setStatusText(localMessages.length > 0 ? '后端未响应，已切换到本地 fallback 会话。' : '后端未响应，已进入本地 mock/fallback 模式。');
      setLastError(message);
      setIsBootstrapped(true);
    }
  };

  const sendMessage = async (prefillQuestion?: string) => {
    const question = (prefillQuestion ?? input).trim();
    if (!question || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setLastError(null);
    setStatusText('正在整理知识库、历史实验和实验上下文...');

    try {
      const response = await fetch('/api/v1/chat/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          context: {
            entry: 'knowledge-chat',
            scope: ['knowledge-base', 'history-experiments', 'method-experience', 'experiment-context'],
            experiment_context: mergedExperimentContext,
          },
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const assistantMessage: ChatMessage = data?.message?.content
        ? {
            ...data.message,
            meta: {
              mode: 'live',
              statusLabel: 'live',
            },
          }
        : buildFallbackAnswer(question);

      setMessages((prev) => [...prev, assistantMessage]);
      setConnectionState(data?.message?.content ? 'live' : 'fallback');
      setStatusText(data?.message?.content ? '已收到知识管理服务回复。' : '后端返回为空，已自动切换 fallback 回复。');
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误';
      setMessages((prev) => [...prev, buildFallbackAnswer(question)]);
      setConnectionState('fallback');
      setStatusText('发送失败，已切换到本地 fallback 回复。');
      setLastError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      await fetch('/api/v1/chat/history', { method: 'DELETE' });
    } catch {
      // ignore network failure and still clear local messages
    }

    const welcome = createWelcomeMessage();
    setMessages([welcome]);
    saveLocalMessages([welcome]);
    setConnectionState('fallback');
    setStatusText('聊天历史已清空，已恢复欢迎状态。');
    setLastError(null);
  };

  if (!isOpen) return null;

  const statusConfig: Record<ConnectionState, { icon: typeof Loader2; tone: string; label: string }> = {
    connecting: {
      icon: Loader2,
      tone: 'border-blue-200 bg-blue-50 text-blue-700',
      label: '连接中',
    },
    live: {
      icon: Wifi,
      tone: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      label: '后端在线',
    },
    fallback: {
      icon: WifiOff,
      tone: 'border-amber-200 bg-amber-50 text-amber-700',
      label: 'Fallback 模式',
    },
    error: {
      icon: AlertCircle,
      tone: 'border-rose-200 bg-rose-50 text-rose-700',
      label: '服务异常',
    },
  };

  const currentStatus = statusConfig[connectionState];
  const StatusIcon = currentStatus.icon;

  return (
    <div className={shellClass}>
      <div className="rounded-t-2xl bg-gradient-to-r from-slate-950 via-blue-900 to-cyan-700 p-4 text-white">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              <h3 className="font-semibold">{title}</h3>
            </div>
            <p className="mt-2 text-xs leading-5 text-blue-50/90">{subtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={clearHistory} className="rounded p-1 transition-colors hover:bg-white/10" title="清空历史">
              <Trash2 className="h-4 w-4" />
            </button>
            {mode === 'drawer' && onClose && (
              <button onClick={onClose} className="rounded p-1 transition-colors hover:bg-white/10" title="关闭窗口">
                <X className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="border-b border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${currentStatus.tone}`}>
            <StatusIcon className={`h-3.5 w-3.5 ${connectionState === 'connecting' ? 'animate-spin' : ''}`} />
            {currentStatus.label}
          </div>
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600">
            <Clock3 className="h-3.5 w-3.5" />
            {statusText}
          </div>
        </div>
        {lastError && (
          <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">
            最近一次错误：{lastError}
          </div>
        )}
      </div>

      <div className="border-b border-slate-200 bg-white p-4">
        <div className="grid gap-3 xl:grid-cols-[1.1fr,0.9fr]">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-950">
              <FlaskConical className="h-4 w-4" /> 当前实验上下文
            </div>
            <div className="mt-3 space-y-2 text-xs leading-5 text-blue-900">
              <p><span className="font-semibold">实验：</span>{mergedExperimentContext.experimentName}</p>
              <p><span className="font-semibold">阶段：</span>{mergedExperimentContext.stage}</p>
              <p><span className="font-semibold">目标：</span>{mergedExperimentContext.objective}</p>
              <p><span className="font-semibold">最新观察：</span>{mergedExperimentContext.latestObservation}</p>
              <p><span className="font-semibold">下一步建议：</span>{mergedExperimentContext.nextSuggestion}</p>
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                <BookOpen className="h-4 w-4" /> 当前检索范围
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {contextItems.map((item) => (
                  <span key={item} className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-700 ring-1 ring-slate-200">
                    {item}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-violet-100 bg-violet-50 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-violet-800">
                <History className="h-4 w-4" /> 推荐追问方向
              </div>
              <p className="mt-2 text-xs leading-5 text-violet-700">
                step 设计、运行异常、参数经验、历史实验对比、下一轮修改策略。
              </p>
            </div>
          </div>
        </div>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto bg-slate-50/70 p-4">
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="mt-8 rounded-2xl border border-dashed border-slate-200 bg-white p-6 text-center text-gray-500">
              <Database className="mx-auto mb-3 h-12 w-12 opacity-50" />
              <p className="font-medium text-slate-700">当前还没有消息</p>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                先从 quick actions 开始，或者直接输入当前实验问题。
              </p>
            </div>
          )}

          {messages.map((msg) => {
            const isFallbackMessage = msg.meta?.mode === 'fallback';

            return (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[88%] rounded-2xl p-4 shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : isFallbackMessage
                        ? 'border border-amber-200 bg-amber-50 text-slate-800'
                        : 'border border-slate-200 bg-white text-slate-800'
                  }`}
                >
                  <div className="whitespace-pre-wrap break-words text-sm leading-6">{msg.content}</div>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] opacity-80">
                    <div className="flex items-center gap-2">
                      <span>{getAgentLabel(msg)}</span>
                      {msg.role === 'assistant' && (
                        <span
                          className={`rounded-full px-2 py-0.5 ${
                            isFallbackMessage
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-emerald-100 text-emerald-700'
                          }`}
                        >
                          {isFallbackMessage ? 'fallback' : 'live'}
                        </span>
                      )}
                    </div>
                    <div>{new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}</div>
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex justify-start">
              <div className="flex max-w-[88%] items-center gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                正在整理知识库、历史实验和实验上下文...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-4 py-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={() => setInput(action.question)}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700 transition-colors hover:bg-slate-100"
            >
              {action.label}
            </button>
          ))}
          <button
            onClick={() => void sendMessage('结合当前实验上下文，帮我总结一下我现在最该问的问题。')}
            className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs text-cyan-700 transition-colors hover:bg-cyan-100"
            disabled={isLoading}
          >
            一键开始
          </button>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
            placeholder="输入你的实验问题，例如：结合当前 step，为什么建议先用 CV 而不是直接做 EIS？（Enter 发送，Shift + Enter 换行）"
            className="min-h-[92px] w-full resize-none border-0 bg-transparent px-2 py-2 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400"
            disabled={isLoading}
          />
          <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-2 pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Sparkles className="h-3.5 w-3.5" />
              无后端结果时自动切换 fallback，保证入口不是空壳。
            </div>
            <button
              onClick={() => void sendMessage()}
              disabled={!input.trim() || isLoading}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              发送
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          欢迎语、quick actions、稳定消息流、状态提示、fallback mock flow 已就位。
        </div>
      </div>
    </div>
  );
}
