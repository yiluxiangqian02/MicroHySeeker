import { useEffect, useRef, useState } from 'react'; // ChatWindow
import { useTranslation } from 'react-i18next';
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

const defaultContextKeys = {
  experimentName: 'chat.context.experimentName',
  stage: 'chat.context.stage',
  objective: 'chat.context.objective',
  latestObservation: 'chat.context.latestObservation',
  nextSuggestion: 'chat.context.nextSuggestion',
};

const quickActionKeys = [
  { labelKey: 'chat.quickActions.askExperiment', questionKey: 'chat.quickActions.askExperimentQ' },
  { labelKey: 'chat.quickActions.askKnowledge', questionKey: 'chat.quickActions.askKnowledgeQ' },
  { labelKey: 'chat.quickActions.askException', questionKey: 'chat.quickActions.askExceptionQ' },
  { labelKey: 'chat.quickActions.askHistory', questionKey: 'chat.quickActions.askHistoryQ' },
];

function createWelcomeMessage(t: (key: string) => string): ChatMessage {
  return {
    id: 'welcome_knowledge_chat',
    role: 'assistant',
    content: [
      t('chat.welcome.line1'),
      t('chat.welcome.line2'),
      t('chat.welcome.line3'),
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

function buildFallbackAnswer(question: string, t: (key: string) => string): ChatMessage {
  const lowered = question.toLowerCase();
  let content = [
    t('chat.fallback.header'),
    t('chat.fallback.description'),
    t('chat.fallback.footer'),
  ].join('\n');

  if (lowered.includes('cv') || lowered.includes('lsv') || lowered.includes('eis') || lowered.includes('dpv') || lowered.includes('扫描速率')) {
    content = [
      t('chat.fallback.cv.header'),
      t('chat.fallback.cv.line1'),
      t('chat.fallback.cv.line2'),
      t('chat.fallback.cv.line3'),
      t('chat.fallback.cv.line4'),
    ].join('\n');
  } else if (lowered.includes('transfer') || lowered.includes('flush') || lowered.includes('evacuate') || lowered.includes('卡住')) {
    content = [
      t('chat.fallback.transfer.header'),
      t('chat.fallback.transfer.checkHeader'),
      t('chat.fallback.transfer.check1'),
      t('chat.fallback.transfer.check2'),
      t('chat.fallback.transfer.check3'),
      t('chat.fallback.transfer.check4'),
      t('chat.fallback.transfer.footer'),
    ].join('\n');
  } else if (lowered.includes('下一轮') || lowered.includes('建议') || lowered.includes('优化') || lowered.includes('改哪里')) {
    content = [
      t('chat.fallback.nextRound.header'),
      t('chat.fallback.nextRound.line1'),
      t('chat.fallback.nextRound.priorityHeader'),
      t('chat.fallback.nextRound.priority1'),
      t('chat.fallback.nextRound.priority2'),
      t('chat.fallback.nextRound.priority3'),
      t('chat.fallback.nextRound.footer'),
    ].join('\n');
  } else if (lowered.includes('历史') || lowered.includes('run') || lowered.includes('相似实验')) {
    content = [
      t('chat.fallback.history.header'),
      t('chat.fallback.history.line1'),
      t('chat.fallback.history.line2'),
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

function getAgentLabel(message: ChatMessage, t: (key: string) => string) {
  if (message.agent_type === 'data_analyst') return t('chat.agentLabels.dataAnalyst');
  if (message.agent_type === 'experiment_designer') return t('chat.agentLabels.experimentDesigner');
  if (message.agent_type === 'knowledge_manager') return t('chat.agentLabels.knowledgeManager');
  return message.role === 'user' ? t('chat.agentLabels.userQuestion') : t('chat.agentLabels.assistantReply');
}

export default function ChatWindow({
  isOpen = true,
  onClose,
  mode = 'drawer',
  title,
  subtitle,
  contextItems,
  experimentContext,
}: ChatWindowProps) {
  const { t } = useTranslation();
  const resolvedTitle = title ?? t('chat.props.title');
  const resolvedSubtitle = subtitle ?? t('chat.props.subtitle');
  const resolvedContextItems = contextItems ?? [t('chat.props.contextItem0'), t('chat.props.contextItem1'), t('chat.props.contextItem2')];
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isBootstrapped, setIsBootstrapped] = useState(false);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [statusText, setStatusText] = useState('');
  const [lastError, setLastError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const defaultExperimentContext: ExperimentContextSummary = {
    experimentName: t(defaultContextKeys.experimentName),
    stage: t(defaultContextKeys.stage),
    objective: t(defaultContextKeys.objective),
    latestObservation: t(defaultContextKeys.latestObservation),
    nextSuggestion: t(defaultContextKeys.nextSuggestion),
  };

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
    setStatusText(t('chat.status.connecting'));
    setLastError(null);

    const localMessages = readLocalMessages();

    try {
      const response = await fetch('/api/v1/chat/history?limit=50');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      const remoteMessages = Array.isArray(data.messages) ? normalizeMessages(data.messages) : [];
      const nextMessages = remoteMessages.length > 0 ? remoteMessages : localMessages.length > 0 ? localMessages : [createWelcomeMessage(t)];

      setMessages(nextMessages);
      setConnectionState('live');
      setStatusText(remoteMessages.length > 0 ? t('chat.statusMessages.backendConnected') : t('chat.statusMessages.backendNoHistory'));
      setIsBootstrapped(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : t('chat.statusMessages.unknownError');
      setMessages(localMessages.length > 0 ? localMessages : [createWelcomeMessage(t)]);
      setConnectionState(localMessages.length > 0 ? 'fallback' : 'error');
      setStatusText(localMessages.length > 0 ? t('chat.statusMessages.fallbackWithLocal') : t('chat.statusMessages.fallbackNoLocal'));
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
    setStatusText(t('chat.statusMessages.processing'));

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
        : buildFallbackAnswer(question, t);

      setMessages((prev) => [...prev, assistantMessage]);
      setConnectionState(data?.message?.content ? 'live' : 'fallback');
      setStatusText(data?.message?.content ? t('chat.statusMessages.receivedReply') : t('chat.statusMessages.emptyReply'));
    } catch (error) {
      const message = error instanceof Error ? error.message : t('chat.statusMessages.unknownError');
      setMessages((prev) => [...prev, buildFallbackAnswer(question, t)]);
      setConnectionState('fallback');
      setStatusText(t('chat.statusMessages.sendFailed'));
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

    const welcome = createWelcomeMessage(t);
    setMessages([welcome]);
    saveLocalMessages([welcome]);
    setConnectionState('fallback');
    setStatusText(t('chat.statusMessages.historyCleared'));
    setLastError(null);
  };

  if (!isOpen) return null;

  const statusConfig: Record<ConnectionState, { icon: typeof Loader2; tone: string; label: string }> = {
    connecting: {
      icon: Loader2,
      tone: 'border-blue-200 bg-blue-50 text-blue-700',
      label: t('chat.statusConfig.connecting'),
    },
    live: {
      icon: Wifi,
      tone: 'border-emerald-200 bg-emerald-50 text-emerald-700',
      label: t('chat.statusConfig.live'),
    },
    fallback: {
      icon: WifiOff,
      tone: 'border-amber-200 bg-amber-50 text-amber-700',
      label: t('chat.statusConfig.fallback'),
    },
    error: {
      icon: AlertCircle,
      tone: 'border-rose-200 bg-rose-50 text-rose-700',
      label: t('chat.statusConfig.error'),
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
              <h3 className="font-semibold">{resolvedTitle}</h3>
            </div>
            <p className="mt-2 text-xs leading-5 text-blue-50/90">{resolvedSubtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={clearHistory} className="rounded p-1 transition-colors hover:bg-white/10" title={t('chat.buttons.clearHistory')}>
              <Trash2 className="h-4 w-4" />
            </button>
            {mode === 'drawer' && onClose && (
              <button onClick={onClose} className="rounded p-1 transition-colors hover:bg-white/10" title={t('chat.buttons.closeWindow')}>
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
                        {t('chat.status.lastError')}{lastError}
          </div>
        )}
      </div>

      <div className="border-b border-slate-200 bg-white p-4">
        <div className="grid gap-3 xl:grid-cols-[1.1fr,0.9fr]">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-blue-950">
              <FlaskConical className="h-4 w-4" /> {t('chat.contextDisplay.title')}
            </div>
            <div className="mt-3 space-y-2 text-xs leading-5 text-blue-900">
              <p><span className="font-semibold">{t('chat.contextDisplay.experiment')}</span>{mergedExperimentContext.experimentName}</p>
              <p><span className="font-semibold">{t('chat.contextDisplay.stage')}</span>{mergedExperimentContext.stage}</p>
              <p><span className="font-semibold">{t('chat.contextDisplay.objective')}</span>{mergedExperimentContext.objective}</p>
              <p><span className="font-semibold">{t('chat.contextDisplay.observation')}</span>{mergedExperimentContext.latestObservation}</p>
              <p><span className="font-semibold">{t('chat.contextDisplay.nextSuggestion')}</span>{mergedExperimentContext.nextSuggestion}</p>
            </div>
          </div>

          <div className="grid gap-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
                <BookOpen className="h-4 w-4" /> {t('chat.retrievalScope.title')}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {resolvedContextItems.map((item) => (
                  <span key={item} className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-700 ring-1 ring-slate-200">
                    {item}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-violet-100 bg-violet-50 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-violet-800">
                <History className="h-4 w-4" /> {t('chat.recommendations.title')}
              </div>
              <p className="mt-2 text-xs leading-5 text-violet-700">
                {t('chat.recommendations.content')}
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
              <p className="font-medium text-slate-700">{t('chat.messages.emptyTitle')}</p>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {t('chat.messages.emptyDescription')}
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
                      <span>{getAgentLabel(msg, t)}</span>
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
                    <div>{new Date(msg.timestamp).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</div>
                  </div>
                </div>
              </div>
            );
          })}

          {isLoading && (
            <div className="flex justify-start">
              <div className="flex max-w-[88%] items-center gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                                {t('chat.status.loading')}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-4 py-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {quickActionKeys.map((action) => (
            <button
              key={action.labelKey}
              onClick={() => setInput(t(action.questionKey))}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700 transition-colors hover:bg-slate-100"
            >
              {t(action.labelKey)}
            </button>
          ))}
          <button
            onClick={() => void sendMessage(t('chat.statusMessages.quickStartQ'))}
            className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-xs text-cyan-700 transition-colors hover:bg-cyan-100"
            disabled={isLoading}
          >
                        {t('chat.buttons.quickStart')}
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
            placeholder={t('chat.input.placeholder')}
            className="min-h-[92px] w-full resize-none border-0 bg-transparent px-2 py-2 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400"
            disabled={isLoading}
          />
          <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-2 pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <Sparkles className="h-3.5 w-3.5" />
                            {t('chat.helpText.fallback')}
            </div>
            <button
              onClick={() => void sendMessage()}
              disabled={!input.trim() || isLoading}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {t('chat.buttons.send')}
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    {t('chat.footer.status')}
        </div>
      </div>
    </div>
  );
}
