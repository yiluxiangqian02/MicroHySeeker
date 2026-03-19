import { ReactNode } from "react";
import { FileText, Beaker, AlertTriangle, Lightbulb, Database } from "lucide-react";
import { KnowledgeItem } from "@/api/knowledge";

interface KnowledgeResultListProps {
  results: Array<{ item: KnowledgeItem; score: number }>;
}

const PARTITION_ICONS: Record<string, ReactNode> = {
  protocols: <FileText className="h-4 w-4" />,
  experiments: <Beaker className="h-4 w-4" />,
  faults: <AlertTriangle className="h-4 w-4" />,
  methods: <Lightbulb className="h-4 w-4" />
};

export function KnowledgeResultList({ results }: KnowledgeResultListProps) {
  if (results.length === 0) {
    return (
      <div className="text-center py-16 text-slate-500">
        <Database className="h-10 w-10 mx-auto text-slate-300 mb-3" />
        <p className="font-medium text-slate-700">No results found</p>
        <p className="text-sm mt-1">Try adjusting your search terms or expanding partitions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {results.map(({ item, score }, i) => (
        <div 
          key={item.id || i} 
          className="bg-white rounded-2xl border border-slate-200 p-5 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer group"
        >
          <div className="flex items-start justify-between mb-2">
            <h3 className="font-semibold text-lg text-slate-900 group-hover:text-blue-700 transition">
              {item.title}
            </h3>
            <div className="flex items-center gap-2 text-xs">
              <span className={`flex items-center gap-1 px-2.5 py-1 rounded-full font-medium ${
                score > 0.8 ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"
              }`}>
                Score: {(score * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-3 mb-3 text-xs">
            <span className="flex items-center gap-1.5 font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
              {PARTITION_ICONS[item.partition] || <Database className="h-4 w-4" />}
              {item.partition}
            </span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-500">
              {new Date(item.updatedAt || item.createdAt).toLocaleDateString()}
            </span>
          </div>

          <p className="text-sm text-slate-600 line-clamp-2 leading-relaxed">
            {item.content}
          </p>

          {(item.tags && item.tags.length > 0) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {item.tags.map(tag => (
                <span key={tag} className="text-[10px] uppercase font-bold tracking-wider text-slate-500 bg-slate-100 px-2 py-1 rounded">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
