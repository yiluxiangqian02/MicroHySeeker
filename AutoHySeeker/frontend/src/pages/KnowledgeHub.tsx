import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  AlertTriangle,
  Beaker,
  CheckCircle2,
  Database,
  FolderOpen,
  Loader2,
  RefreshCw,
  Search,
  Sparkles,
  Upload,
  XCircle,
} from "lucide-react";

import ChatWindow from "@/components/ChatWindow";
import { KnowledgeResultList } from "@/components/knowledge/KnowledgeResultList";
import { KnowledgeSearchBar } from "@/components/knowledge/KnowledgeSearchBar";
import { ingestApi, IngestTask, knowledgeApi, KnowledgeItem } from "@/api/knowledge";

type ScoredKnowledgeItem = { item: KnowledgeItem; score: number };

// ── Ingest status badge ───────────────────────────────────────────────────────
function IngestStatusBadge({ task }: { task: IngestTask | null }) {
  const { t } = useTranslation();
  if (!task || task.status === "idle") return null;

  const map: Record<string, { icon: React.ReactNode; cls: string; label: string }> = {
    pending: {
      icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
      cls: "bg-amber-100 text-amber-700 border-amber-200",
      label: t("knowledge.ingest.pending"),
    },
    running: {
      icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
      cls: "bg-blue-100 text-blue-700 border-blue-200",
      label: t("knowledge.ingest.running"),
    },
    completed: {
      icon: <CheckCircle2 className="h-3.5 w-3.5" />,
      cls: "bg-emerald-100 text-emerald-700 border-emerald-200",
      label: t("knowledge.ingest.completed"),
    },
    failed: {
      icon: <XCircle className="h-3.5 w-3.5" />,
      cls: "bg-red-100 text-red-700 border-red-200",
      label: t("knowledge.ingest.failed"),
    },
  };

  const style = map[task.status] ?? map.pending;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${style.cls}`}>
      {style.icon}
      {style.label}
    </span>
  );
}

export function KnowledgeHub() {
  const { t } = useTranslation();
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ScoredKnowledgeItem[]>([]);
  const [resultLabel, setResultLabel] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Ingest state
  const [ingestTask, setIngestTask] = useState<IngestTask | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [defaultDir, setDefaultDir] = useState<{ path: string; count: number } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch default MinerU dir on mount
  useEffect(() => {
    ingestApi.getDefaultDir().then((info) => {
      setDefaultDir({ path: info.default_mineru_output, count: info.document_count });
    }).catch(() => {/* ignore */});
  }, []);

  // Poll ingest status while running/pending
  useEffect(() => {
    const isActive = ingestTask?.status === "running" || ingestTask?.status === "pending";
    if (isActive && !pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const status = await ingestApi.getStatus(ingestTask?.task_id);
          const latest = status.latest ?? (status as unknown as IngestTask);
          setIngestTask(latest);
          if (latest.status === "completed" || latest.status === "failed") {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            // refresh default dir count after completion
            ingestApi.getDefaultDir().then((info) => {
              setDefaultDir({ path: info.default_mineru_output, count: info.document_count });
            }).catch(() => {/* ignore */});
          }
        } catch {
          clearInterval(pollRef.current!);
          pollRef.current = null;
        }
      }, 3000);
    }
    return () => {
      if (!isActive && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [ingestTask]);

  const startIngest = useCallback(async () => {
    setIngestError(null);
    try {
      const task = await ingestApi.startIngest({});
      setIngestTask(task);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("knowledge.ingest.startFailed");
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setIngestError(detail ?? msg);
    }
  }, [t]);

  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setResultLabel("");
      setError(null);
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const response = await knowledgeApi.search({ query, limit: 10 });
      setSearchResults(response.results);
      setResultLabel(`${t("knowledge.searchResults")} · ${query}`);
    } catch (err) {
      setSearchResults([]);
      setError(err instanceof Error ? err.message : t("knowledge.searchFailed"));
    } finally {
      setIsSearching(false);
    }
  }, [t]);

  const loadExperimentExamples = useCallback(async () => {
    setIsSearching(true);
    setError(null);
    try {
      const response = await knowledgeApi.getSimilarExperiments({ Fe: 0.3, Co: 0.3, Ni: 0.4 }, 5);
      setSearchResults(response.results);
      setResultLabel(t("knowledge.experimentMatches"));
    } catch (err) {
      setSearchResults([]);
      setError(err instanceof Error ? err.message : t("knowledge.experimentMatchFailed"));
    } finally {
      setIsSearching(false);
    }
  }, [t]);

  const loadFaultExamples = useCallback(async () => {
    setIsSearching(true);
    setError(null);
    try {
      const response = await knowledgeApi.getFaultHistory("communication_timeout", 5);
      setSearchResults(response.results);
      setResultLabel(t("knowledge.faultHistory"));
    } catch (err) {
      setSearchResults([]);
      setError(err instanceof Error ? err.message : t("knowledge.faultHistoryFailed"));
    } finally {
      setIsSearching(false);
    }
  }, [t]);

  const isIngesting = ingestTask?.status === "running" || ingestTask?.status === "pending";

  return (
    <div className="space-y-8 p-6">
      {/* ── Hero banner ──────────────────────────────────────────────────── */}
      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-indigo-900 to-cyan-800 p-8 text-white shadow-sm">
        <div className="grid gap-6 lg:grid-cols-[1.35fr,1fr] lg:items-center">
          <div>
            <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.2em] text-cyan-100">
              <Database className="h-4 w-4" /> {t("knowledge.openviking_integration")}
            </p>
            <h1 className="mt-3 text-3xl font-bold">{t("knowledge.title")}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-cyan-50/90">
              {t("knowledge.heroDesc")}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 justify-items-end">
            <button
              type="button"
              onClick={loadExperimentExamples}
              className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-5 py-2.5 font-medium text-white transition backdrop-blur-sm hover:bg-white/20"
            >
              <Beaker className="h-5 w-5" />
              {t("knowledge.loadExperiments")}
            </button>
            <button
              type="button"
              onClick={loadFaultExamples}
              className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-5 py-2.5 font-medium text-white transition backdrop-blur-sm hover:bg-white/20"
            >
              <AlertTriangle className="h-5 w-5" />
              {t("knowledge.loadFaults")}
            </button>
          </div>
        </div>
      </section>

      {/* ── MinerU Import Panel ──────────────────────────────────────────── */}
      <section className="rounded-2xl border border-indigo-100 bg-indigo-50 p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Upload className="h-5 w-5 flex-shrink-0 text-indigo-600" />
              <h2 className="text-base font-semibold text-indigo-900">{t("knowledge.ingest.title")}</h2>
              <IngestStatusBadge task={ingestTask} />
            </div>
            <p className="mt-1 text-sm text-indigo-700">{t("knowledge.ingest.desc")}</p>
            {defaultDir && (
              <p className="mt-1.5 flex items-center gap-1 truncate text-xs text-indigo-500">
                <FolderOpen className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="truncate">{defaultDir.path}</span>
                <span className="flex-shrink-0 rounded-full bg-indigo-200 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
                  {defaultDir.count} {t("knowledge.ingest.docs")}
                </span>
              </p>
            )}
            {ingestTask?.status === "failed" && ingestTask.error && (
              <p className="mt-2 text-xs text-red-600">{t("knowledge.ingest.errorPrefix")}{ingestTask.error}</p>
            )}
            {ingestTask?.status === "completed" && (
              <p className="mt-2 text-xs text-emerald-700">{t("knowledge.ingest.successMsg")}</p>
            )}
            {ingestError && (
              <p className="mt-2 text-xs text-red-600">{ingestError}</p>
            )}
          </div>
          <div className="flex flex-shrink-0 items-center gap-2">
            {ingestTask && !isIngesting && (
              <button
                type="button"
                title={t("knowledge.ingest.refresh")}
                onClick={() => ingestApi.getStatus(ingestTask.task_id).then((s) => {
                  const latest = s.latest ?? (s as unknown as IngestTask);
                  setIngestTask(latest);
                }).catch(() => {})}
                className="rounded-lg border border-indigo-200 bg-white p-2 text-indigo-600 transition hover:bg-indigo-100"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            )}
            <button
              type="button"
              disabled={isIngesting}
              onClick={startIngest}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isIngesting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {isIngesting ? t("knowledge.ingest.running") : t("knowledge.ingest.button")}
            </button>
          </div>
        </div>
      </section>

      {/* ── Search bar ───────────────────────────────────────────────────── */}
      <section className="relative z-10 mx-auto -mt-4 max-w-4xl px-4">
        <KnowledgeSearchBar onSearch={handleSearch} isLoading={isSearching} />
      </section>

      {/* ── Results + Chat ───────────────────────────────────────────────── */}
      <section className="grid gap-6 pt-4 xl:grid-cols-[1fr,1fr]">
        {/* Left: search results */}
        <div className="space-y-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900">{resultLabel || t("knowledge.searchResults")}</h2>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-500">
              {searchResults.length} {t("knowledge.items")}
            </span>
          </div>

          {error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
              {error}
            </div>
          ) : searchResults.length === 0 && !isSearching ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-slate-500">
              <Search className="mx-auto mb-3 h-8 w-8 text-slate-300" />
              {t("knowledge.emptyHint")}
            </div>
          ) : (
            <KnowledgeResultList results={searchResults} />
          )}
        </div>

        {/* Right: AI Chat */}
        <div className="sticky top-6 flex h-[660px] flex-col">
          <div className="mb-4 flex items-center gap-2 px-2 text-slate-900">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            <h2 className="text-xl font-bold">{t("knowledge.assistant")}</h2>
            <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
              RAG
            </span>
          </div>
          <div className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <ChatWindow
              mode="embedded"
              contextItems={[
                t("knowledge.chat.context.search"),
                t("knowledge.chat.context.experiments"),
                t("knowledge.chat.context.faults"),
              ]}
              experimentContext={{
                experimentName: t("knowledge.chat.experimentName"),
                stage: t("knowledge.chat.stage"),
                objective: t("knowledge.chat.objective"),
                latestObservation: t("knowledge.chat.observation"),
                nextSuggestion: t("knowledge.chat.suggestion"),
              }}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
