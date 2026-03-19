import { Link } from "react-router-dom";
import { ArrowRight, Beaker, CheckCircle2, Clock, XCircle } from "lucide-react";

export interface RecentExperiment {
  id: string;
  name: string;
  status: "running" | "completed" | "failed";
  timeAgo: string;
}

export function RecentExperimentsCard({ experiments }: { experiments: RecentExperiment[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-900">Recent Experiments</h3>
        <Link
          to="/experiments"
          className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
        >
          View All <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="flex-1 p-2">
        {experiments.length === 0 ? (
          <div className="flex h-full items-center justify-center p-4 text-sm text-slate-500">
            No recent experiments.
          </div>
        ) : (
          <ul className="space-y-1">
            {experiments.map((exp) => (
              <li key={exp.id}>
                <Link
                  to={`/experiments/${exp.id}`}
                  className="flex items-center justify-between rounded-xl px-3 py-2 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                      <Beaker className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-900">{exp.name}</p>
                      <p className="text-xs text-slate-500">{exp.timeAgo}</p>
                    </div>
                  </div>
                  <div className="ml-4 shrink-0">
                    {exp.status === "running" && <Clock className="h-5 w-5 text-blue-500" />}
                    {exp.status === "completed" && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                    {exp.status === "failed" && <XCircle className="h-5 w-5 text-red-500" />}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
