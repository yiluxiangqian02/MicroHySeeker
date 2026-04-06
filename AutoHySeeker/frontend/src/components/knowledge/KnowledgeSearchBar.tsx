import { Search, Loader2 } from "lucide-react";
import { useState, FormEvent, useEffect, useRef } from "react";
import { useDebounce } from "@/hooks/useDebounce";

interface KnowledgeSearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function KnowledgeSearchBar({ onSearch, isLoading }: KnowledgeSearchBarProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 500);
  const isMounted = useRef(false);

  // Trigger search when debounced query changes, but skip the initial mount
  useEffect(() => {
    if (!isMounted.current) {
      isMounted.current = true;
      return;
    }
    if (debouncedQuery.trim()) {
      onSearch(debouncedQuery);
    } else {
      onSearch("");
    }
  }, [debouncedQuery, onSearch]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto">
      <div className="relative flex items-center">
        <div className="absolute left-4 text-slate-400 pointer-events-none">
          <Search className="h-5 w-5" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search OpenViking Knowledge Base (e.g. HER catalyst protocols...)"
          className="w-full h-14 pl-12 pr-12 rounded-2xl border-2 border-slate-200 bg-white text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/10 transition-all text-lg placeholder:text-slate-400"
        />
        {isLoading && (
          <div className="absolute right-4 text-blue-500">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        )}
      </div>
      
      <div className="mt-3 flex items-center justify-center gap-2 text-xs font-medium text-slate-500">
        <span>Partitions:</span>
        <span className="px-2 py-0.5 rounded bg-slate-100 cursor-pointer hover:bg-slate-200 transition">protocols</span>
        <span className="px-2 py-0.5 rounded bg-slate-100 cursor-pointer hover:bg-slate-200 transition">experiments</span>
        <span className="px-2 py-0.5 rounded bg-slate-100 cursor-pointer hover:bg-slate-200 transition">faults</span>
      </div>
    </form>
  );
}
