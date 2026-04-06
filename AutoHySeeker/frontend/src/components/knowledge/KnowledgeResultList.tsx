import { ReactNode } from "react";
import { AlertTriangle, Beaker, Database, FileText, Lightbulb } from "lucide-react";

import { KnowledgeItem } from "@/api/knowledge";

interface KnowledgeResultListProps {
  results: Array<{ item: KnowledgeItem; score: number }>;
}

const PARTITION_ICONS: Record<string, () => ReactNode> = {
  protocols: () => <FileText className="h-4 w-4" />,
  experiments: () => <Beaker className="h-4 w-4" />,
  faults: () => <AlertTriangle className="h-4 w-4" />,
  methods: () => <Lightbulb className="h-4 w-4" />,
};

export function KnowledgeResultList({ results }: KnowledgeResultListProps) {
  if (results.length === 0) {
    return (
      <div className="py-16 text-center text-slate-500">
        <Database className="mx-auto mb-3 h-10 w-10 text-slate-300" />
        <p className="font-medium text-slate-700">No results found</p>
        <p className="mt-1 text-sm">Try adjusting your search terms or expanding partitions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {results.map(({ item, score }, index) => (
        <div
          key={item.id || index}
          className="group cursor-pointer rounded-2xl border border-slate-200 bg-white p-5 transition-all hover:border-blue-300 hover:shadow-md"
        >
          <div className="mb-2 flex items-start justify-between">
            <h3 className="text-lg font-semibold text-slate-900 transition group-hover:text-blue-700">
              {item.title}
            </h3>
            <div className="flex items-center gap-2 text-xs">
              <span
                className={`flex items-center gap-1 rounded-full px-2.5 py-1 font-medium ${
                  score > 0.8 ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-600"
                }`}
              >
                Score: {(score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <div className="mb-3 flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1.5 rounded bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700">
              {PARTITION_ICONS[item.partition]?.() ?? <Database className="h-4 w-4" />}
              {item.partition}
            </span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-500">
              {new Date(item.updatedAt || item.createdAt).toLocaleDateString()}
            </span>
          </div>

          <p className="line-clamp-3 text-sm leading-relaxed text-slate-600">{item.content}</p>

          {item.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {item.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500"
                >
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
