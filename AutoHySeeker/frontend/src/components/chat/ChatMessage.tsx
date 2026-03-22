import { ChatMessagePayload } from "@/api/chat";
import { User, Info, BrainCircuit } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface ChatMessageProps {
  message: ChatMessagePayload;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 text-xs text-slate-500 font-medium border border-slate-200">
          <Info className="h-3.5 w-3.5" />
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-4 w-full ${isUser ? "flex-row-reverse" : "flex-row"} mb-6`}>
      <div className={`shrink-0 h-8 w-8 rounded-full flex items-center justify-center border shadow-sm ${
        isUser ? "bg-blue-600 border-blue-700 text-white" : "bg-white border-slate-200 text-slate-600"
      }`}>
        {isUser ? <User className="h-4 w-4" /> : <BrainCircuit className="h-4 w-4" />}
      </div>
      
      <div className={`flex flex-col max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div className="flex items-center gap-2 mb-1.5 px-1">
          <span className="text-xs font-medium text-slate-500">
            {isUser ? "You" : `Agent ${message.agentId || "Core"}`}
          </span>
          <span className="text-[10px] text-slate-400">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
        
        <div className={`rounded-2xl px-5 py-3.5 text-sm shadow-sm ${
          isUser 
            ? "bg-blue-600 text-white rounded-tr-none" 
            : "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
        }`}>
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
