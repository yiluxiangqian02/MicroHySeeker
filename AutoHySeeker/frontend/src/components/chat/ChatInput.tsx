import { useState, FormEvent } from "react";
import { Send, CornerDownLeft } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    
    onSend(input);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <div className="relative flex-1">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Ask AutoHySeeker agents..."
          disabled={disabled}
          className="w-full resize-none rounded-xl border border-slate-300 bg-white pl-4 pr-12 py-3.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-500"
          rows={1}
          style={{ minHeight: "52px", maxHeight: "200px" }}
        />
        <div className="absolute right-3 top-3.5 hidden sm:flex items-center gap-1 text-[10px] font-medium text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded pointer-events-none">
          <CornerDownLeft className="h-3 w-3" /> Enter
        </div>
      </div>
      
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="flex shrink-0 items-center justify-center h-[52px] w-[52px] rounded-xl bg-blue-600 text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-slate-200 disabled:text-slate-400 transition"
      >
        <Send className="h-5 w-5 ml-1" />
      </button>
    </form>
  );
}
