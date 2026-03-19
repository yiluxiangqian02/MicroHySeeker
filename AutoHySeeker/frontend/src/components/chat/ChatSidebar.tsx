import { ChatSession } from "@/api/chat";
import { MessageSquarePlus, MessageSquare } from "lucide-react";

interface ChatSidebarProps {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ChatSidebar({ sessions, activeId, onSelect, onNew }: ChatSidebarProps) {
  return (
    <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200">
      <div className="p-4 border-b border-slate-200 bg-white">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 text-white px-4 py-2.5 text-sm font-medium hover:bg-blue-700 transition"
        >
          <MessageSquarePlus className="h-4 w-4" />
          New Conversation
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSelect(session.id)}
            className={`w-full flex items-start gap-3 p-3 rounded-lg text-left transition ${
              activeId === session.id
                ? "bg-blue-100/50 text-blue-900 border border-blue-200/50 shadow-sm"
                : "text-slate-700 hover:bg-white border border-transparent hover:border-slate-200"
            }`}
          >
            <MessageSquare className={`h-5 w-5 shrink-0 mt-0.5 ${activeId === session.id ? "text-blue-500" : "text-slate-400"}`} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{session.title}</p>
              <p className="text-xs text-slate-500 mt-1">
                {new Date(session.updatedAt).toLocaleDateString()}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
