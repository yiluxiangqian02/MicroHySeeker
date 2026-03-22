import { useTranslation } from "react-i18next";
import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { motion } from "framer-motion";
import { Bot, RefreshCw, ChevronDown } from "lucide-react";

const SCROLL_THRESHOLD = 100; // pixels from bottom to consider "at bottom"

export function Chat() {
  const { t } = useTranslation();
  const { 
    sessions, 
    activeSessionId, 
    messages, 
    isWaitingForResponse,
    fetchSessions, 
    setActiveSession, 
    createNewSession, 
    sendMessage 
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [isUserScrolling, setIsUserScrolling] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // Detect if user is scrolling
  const handleScroll = () => {
    setIsUserScrolling(true);
    const el = containerRef.current;
    if (!el) return;

    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsAtBottom(distance < SCROLL_THRESHOLD);
  };

  // Auto-scroll only if user is at bottom or just received first message
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Use requestAnimationFrame to ensure DOM is updated
    const timer = requestAnimationFrame(() => {
      // If user is already at bottom, auto-scroll to new messages
      if (isAtBottom && !isUserScrolling) {
        el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
      }
      
      // Reset scroll state after a brief delay
      setIsUserScrolling(false);
    });

    return () => cancelAnimationFrame(timer);
  }, [messages, isAtBottom, isUserScrolling]);

  // Scroll to bottom when there are new messages and user hasn't scrolled
  const scrollToBottom = () => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] -m-6 rounded-tl-2xl overflow-hidden border-t border-l border-slate-200 bg-white">
      {/* Sidebar for Sessions */}
      <div className="w-72 shrink-0">
        <ChatSidebar 
          sessions={sessions} 
          activeId={activeSessionId} 
          onSelect={setActiveSession} 
          onNew={createNewSession}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-slate-50/50">
        
        {/* Chat Header */}
        <div className="h-16 px-6 border-b border-slate-200 bg-white flex items-center shadow-sm z-10 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-blue-100/50 flex items-center justify-center border border-blue-200/50 text-blue-600">
              <Bot className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-semibold text-slate-900 leading-tight">
                {sessions.find(s => s.id === activeSessionId)?.title || t('chat.assistant')}
              </h2>
              <p className="text-xs text-slate-500">{t('chat.contextAware')}</p>
            </div>
          </div>
        </div>

        {/* Message Trace */}
        <div 
          ref={containerRef} 
          className="flex-1 overflow-y-auto p-6 relative"
          onScroll={handleScroll}
        >
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 mt-32">
                <Bot className="h-12 w-12 text-slate-300 mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">{t('chat.welcomeTitle')}</h3>
                <p className="text-sm max-w-sm">
                  {t('chat.welcomeDesc')}
                </p>
              </div>
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                
                {isWaitingForResponse && (
                  <div className="flex gap-4 w-full flex-row">
                     <div className="shrink-0 h-8 w-8 rounded-full flex items-center justify-center border border-slate-200 bg-white text-slate-400 shadow-sm">
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      </div>
                      <div className="bg-slate-100 rounded-2xl rounded-tl-none px-4 py-3 flex items-center gap-1.5 h-10">
                        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </motion.div>
            )}
          </div>

          {/* "Scroll to Bottom" Button (shown when not at bottom) */}
          {!isAtBottom && messages.length > 0 && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-6 right-6 inline-flex items-center gap-1.5 px-3 py-2 rounded-full bg-blue-600 text-white text-xs font-medium shadow-lg hover:bg-blue-700 transition animate-pulse"
            >
              <ChevronDown className="h-4 w-4" />
              {t('chat.scrollToBottom')}
            </button>
          )}
        </div>

        {/* Input Area */}
        <div className="p-6 bg-white border-t border-slate-200 shrink-0">
          <div className="max-w-3xl mx-auto">
            <ChatInput 
              onSend={(msg) => sendMessage(msg)} 
              disabled={isWaitingForResponse || !activeSessionId}
            />
            <p className="text-center text-[10px] text-slate-400 mt-3">
              {t('chat.disclaimer')}
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
