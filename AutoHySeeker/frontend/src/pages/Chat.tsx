import { useTranslation } from "react-i18next";
import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chatStore";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { motion } from "framer-motion";
import { Bot, RefreshCw } from "lucide-react";

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

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

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
                {sessions.find(s => s.id === activeSessionId)?.title || "Agent Assistant"}
              </h2>
              <p className="text-xs text-slate-500">Multimodal Research Agents · Context Aware</p>
            </div>
          </div>
        </div>

        {/* Message Trace */}
        <div ref={containerRef} className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 mt-32">
                <Bot className="h-12 w-12 text-slate-300 mb-4" />
                <h3 className="text-lg font-medium text-slate-900 mb-2">How can I help you today?</h3>
                <p className="text-sm max-w-sm">
                  You can ask about experiment anomalies, search the open knowledge base, or request suggestions for the next iteration.
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
        </div>

        {/* Input Area */}
        <div className="p-6 bg-white border-t border-slate-200 shrink-0">
          <div className="max-w-3xl mx-auto">
            <ChatInput 
              onSend={(msg) => sendMessage(msg)} 
              disabled={isWaitingForResponse || !activeSessionId}
            />
            <p className="text-center text-[10px] text-slate-400 mt-3">
              AI Agents can make mistakes. Consider verifying critical experiment suggestions.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
