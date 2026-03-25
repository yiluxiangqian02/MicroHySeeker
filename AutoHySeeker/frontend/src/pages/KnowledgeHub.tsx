import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { AlertTriangle, Beaker, Database, Search, Sparkles } from "lucide-react";

import ChatWindow from "@/components/ChatWindow";
import { KnowledgeResultList } from "@/components/knowledge/KnowledgeResultList";
import { KnowledgeSearchBar } from "@/components/knowledge/KnowledgeSearchBar";
import { knowledgeApi, KnowledgeItem } from "@/api/knowledge";

type ScoredKnowledgeItem = { item: KnowledgeItem; score: number };

export function KnowledgeHub() {
  const { t } = useTranslation();
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<ScoredKnowledgeItem[]>([]);
  const [resultLabel, setResultLabel] = useState("Search Results");
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setResultLabel("Search Results");
      setError(null);
      return;
    }

    setIsSearching(true);
    setError(null);
    try {
      const response = await knowledgeApi.search({ query, limit: 10 });
      setSearchResults(response.results);
      setResultLabel(`Search Results · ${query}`);
    } catch (err) {
      setSearchResults([]);
      setError(err instanceof Error ? err.message : "Failed to search knowledge base");
    } finally {
      setIsSearching(false);
    }
  }, []);

  const loadExperimentExamples = useCallback(async () => {
    setIsSearching(true);
    setError(null);
    try {
      const response = await knowledgeApi.getSimilarExperiments({ Fe: 0.3, Co: 0.3, Ni: 0.4 }, 5);
      setSearchResults(response.results);
      setResultLabel("Experiment Matches");
    } catch (err) {
      setSearchResults([]);
      setError(err instanceof Error ? err.message : "Failed to load experiment matches");
    } finally {
      setIsSearching(false);
    }
  }, []);

  const loadFaultExamples = useCallback(async () => {
    setIsSearching(true);
    setError(null);
    try {
      const response = await knowledgeApi.getFaultHistory("communication_timeout", 5);
      setSearchResults(response.results);
      setResultLabel("Fault History");
    } catch (err) {
      setSearchResults([]);
      setError(err instanceof Error ? err.message : "Failed to load fault history");
    } finally {
      setIsSearching(false);
    }
  }, []);

  return (
    <motion.div
      className="space-y-8 p-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-indigo-900 to-cyan-800 p-8 text-white shadow-sm">
        <div className="grid gap-6 lg:grid-cols-[1.35fr,1fr] lg:items-center">
          <div>
            <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.2em] text-cyan-100">
              <Database className="h-4 w-4" /> OpenViking Integration
            </p>
            <h1 className="mt-3 text-3xl font-bold">{t("knowledge.title", "Knowledge Hub")}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-cyan-50/90">
              Vector + structural search powered by OpenViking. Phase 1 currently exposes search,
              similar experiment lookup, and fault history lookup. Ingest and item detail actions are
              intentionally hidden until the backend routes are available.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 justify-items-end">
            <button
              type="button"
              onClick={loadExperimentExamples}
              className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-5 py-2.5 font-medium text-white transition backdrop-blur-sm hover:bg-white/20"
            >
              <Beaker className="h-5 w-5" />
              Load Experiments
            </button>
            <button
              type="button"
              onClick={loadFaultExamples}
              className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-5 py-2.5 font-medium text-white transition backdrop-blur-sm hover:bg-white/20"
            >
              <AlertTriangle className="h-5 w-5" />
              Load Faults
            </button>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto -mt-12 max-w-4xl px-4">
        <KnowledgeSearchBar onSearch={handleSearch} isLoading={isSearching} />
      </section>

      <section className="grid gap-6 pt-4 xl:grid-cols-[1fr,1fr]">
        <div className="space-y-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900">{resultLabel}</h2>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-500">
              {searchResults.length} items
            </span>
          </div>

          {error ? (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
              {error}
            </div>
          ) : searchResults.length === 0 && !isSearching ? (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center text-slate-500">
              <Search className="mx-auto mb-3 h-8 w-8 text-slate-300" />
              Start with a search query, or load the built-in experiment/fault examples.
            </div>
          ) : (
            <KnowledgeResultList results={searchResults} />
          )}
        </div>

        <div className="sticky top-6 flex h-[600px] flex-col">
          <div className="mb-4 flex items-center gap-2 px-2 text-slate-900">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            <h2 className="text-xl font-bold">{t("knowledge.assistant", "Knowledge Assistant")}</h2>
          </div>
          <div className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <ChatWindow
              mode="embedded"
              contextItems={["OpenViking Search", "Experiment Matches", "Fault History"]}
              experimentContext={{
                experimentName: "Global Knowledge Query",
                stage: "Ready",
                objective: "Summarize search results and answer domain questions with the current OpenViking-backed APIs.",
                latestObservation: "Knowledge ingest/recent/detail actions remain disabled in Phase 1.",
                nextSuggestion: "Try querying a fault type or load similar experiments from the quick actions.",
              }}
            />
          </div>
        </div>
      </section>
    </motion.div>
  );
}
