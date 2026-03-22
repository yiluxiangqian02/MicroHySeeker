import { useTranslation } from "react-i18next";
import { motion } from 'framer-motion';
import { Database, Sparkles, Plus } from 'lucide-react';
import ChatWindow from '@/components/ChatWindow';
import { KnowledgeSearchBar } from '@/components/knowledge/KnowledgeSearchBar';
import { KnowledgeResultList } from '@/components/knowledge/KnowledgeResultList';
import { useState } from 'react';
import { KnowledgeItem } from '@/api/knowledge';

// Mock Data for local frontend iteration, waiting for P1-20
const MOCK_RESULTS: Array<{item: KnowledgeItem, score: number}> = [
  {
    score: 0.92,
    item: {
      id: "k1",
      partition: "protocols",
      title: "Standard HER Catalyst Preparation",
      content: "Detailed procedure for preparing Ni-Fe based catalyst on carbon cloth. Includes ink formulation (5% Nafion, ethanol/water 1:3), sonication timing (30m), and drop-casting volumes to achieve 1.0 mg/cm² loading.",
      tags: ["HER", "Preparation", "Catalyst"],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    }
  },
  {
    score: 0.85,
    item: {
      id: "k2",
      partition: "faults",
      title: "CV Curve Noise Troubleshooting",
      content: "If the Cyclic Voltammetry (CV) curve shows high frequency noise (wavy lines), check the Ag/AgCl reference electrode connection. Secondary cause: uncompensated iR drop or trapped bubbles in the microfluidic channel.",
      tags: ["Diagnostics", "CV", "Noise"],
      createdAt: new Date(Date.now() - 86400000).toISOString(),
      updatedAt: new Date(Date.now() - 86400000).toISOString()
    }
  }
];

export function KnowledgeHub() {
  const { t } = useTranslation();
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<Array<{item: KnowledgeItem, score: number}> | null>(null);

  const handleSearch = async (query: string) => {
    if (!query) {
      setSearchResults(null);
      return;
    }
    
    setIsSearching(true);
    // Simulate API delay covering P1-20 integration
    await new Promise(resolve => setTimeout(resolve, 600));
    setSearchResults(MOCK_RESULTS);
    setIsSearching(false);
  };

  return (
    <motion.div
      className="space-y-8 p-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-r from-slate-950 via-indigo-900 to-cyan-800 p-8 text-white shadow-sm">
        <div className="grid gap-6 lg:grid-cols-[1.35fr,1fr] lg:items-center">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-100 flex items-center gap-2">
              <Database className="h-4 w-4" /> OpenViking Integration
            </p>
            <h1 className="mt-3 text-3xl font-bold">{t('knowledge.title', 'Knowledge Hub')}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-cyan-50/90">
              Vector + Structural search powered by OpenViking. Allows agents and users to efficiently fetch protocols, historical experiments, and troubleshooting methods directly into the experimentation workflow.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1 justify-items-end">
            <button className="flex items-center gap-2 bg-white/10 hover:bg-white/20 text-white border border-white/20 px-5 py-2.5 rounded-xl font-medium transition backdrop-blur-sm">
              <Plus className="h-5 w-5" />
              Ingest New Knowledge 
            </button>
          </div>
        </div>
      </section>

      <section className="max-w-4xl mx-auto -mt-12 relative z-10 px-4">
        <KnowledgeSearchBar onSearch={handleSearch} isLoading={isSearching} />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr,1fr] pt-4">
        {/* Left Column: Search Results or Default View */}
        <div className="space-y-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-slate-900">
              {searchResults ? t('knowledge.search_results', 'Search Results') : t('knowledge.recent_popular', 'Recent & Popular')}
            </h2>
            {searchResults && (
              <span className="text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full font-medium">
                {searchResults.length} items found
              </span>
            )}
          </div>
          
          <KnowledgeResultList results={searchResults || MOCK_RESULTS} />
        </div>

        {/* Right Column: Embedded Chat & Context tools */}
        <div className="flex flex-col h-[600px] sticky top-6">
          <div className="flex items-center gap-2 text-slate-900 mb-4 px-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            <h2 className="text-xl font-bold">{t('knowledge.assistant', 'Knowledge Assistant')}</h2>
          </div>
          <div className="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
            <ChatWindow
              mode="embedded"
              contextItems={['OpenViking Vectors', 'Search Results Context', 'Historical Run Summary']}
              experimentContext={{
                experimentName: 'Global Knowledge Query',
                stage: 'Ready',
                objective: 'Help users summarize search results and ask open-ended domain questions.',
                latestObservation: 'Agent C3 connected to OpenViking cluster.',
                nextSuggestion: 'Try asking: "What is the relation between flow rate constraint and signal noise?"',
              }}
            />
          </div>
        </div>
      </section>
    </motion.div>
  );
}
