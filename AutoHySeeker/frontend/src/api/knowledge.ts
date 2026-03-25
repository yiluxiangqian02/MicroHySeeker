import { apiClient } from "./client";

export interface KnowledgeItem {
  id: string;
  partition: string;
  title: string;
  content: string;
  tags: string[];
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface KnowledgeSearchRequest {
  query: string;
  partitions?: string[];
  limit?: number;
}

interface KnowledgeSearchBackendItem {
  uri?: string;
  content?: string;
  score?: number;
  metadata?: Record<string, unknown>;
}

interface KnowledgeSearchResponse {
  count: number;
  items: KnowledgeSearchBackendItem[];
}

interface ExperimentQueryResponse {
  count: number;
  items: Array<Record<string, unknown>>;
}

interface FaultQueryResponse {
  count: number;
  items: Array<Record<string, unknown>>;
}

const nowIso = () => new Date().toISOString();

const titleFromUri = (uri?: string, fallback: string = "Knowledge Record") => {
  if (!uri) {
    return fallback;
  }
  const trimmed = uri.replace(/\/+$/, "");
  const segments = trimmed.split("/");
  return decodeURIComponent(segments[segments.length - 1] || fallback);
};

const normalizeTags = (metadata?: Record<string, unknown>) => {
  const partition = typeof metadata?.partition === "string" ? metadata.partition : undefined;
  return partition ? [partition] : [];
};

const toKnowledgeItem = (
  item: KnowledgeSearchBackendItem,
  partitionFallback: string,
): KnowledgeItem => {
  const timestamp = nowIso();
  const partition =
    typeof item.metadata?.partition === "string" ? item.metadata.partition : partitionFallback;
  const uri = typeof item.uri === "string" ? item.uri : undefined;

  return {
    id: uri || `${partition}-${timestamp}`,
    partition,
    title: titleFromUri(uri),
    content: item.content || "",
    tags: normalizeTags(item.metadata),
    metadata: item.metadata,
    createdAt: timestamp,
    updatedAt: timestamp,
  };
};

const toScoredResults = (
  items: KnowledgeSearchBackendItem[],
  partitionFallback: string,
): Array<{ item: KnowledgeItem; score: number }> =>
  items.map((item) => ({
    item: toKnowledgeItem(item, partitionFallback),
    score: typeof item.score === "number" ? item.score : 0.5,
  }));

export const knowledgeApi = {
  search: async (req: KnowledgeSearchRequest) => {
    const res = await apiClient.get<KnowledgeSearchResponse>("/api/knowledge/search", {
      params: {
        query: req.query,
        partitions: req.partitions?.join(","),
        top_k: req.limit ?? 10,
      },
    });
    return {
      results: toScoredResults(res.data.items, "knowledge"),
      total: res.data.count,
    };
  },

  getSimilarExperiments: async (params: Record<string, number>, topK: number = 5) => {
    const res = await apiClient.get<ExperimentQueryResponse>("/api/knowledge/experiments", {
      params: {
        params: JSON.stringify(params),
        top_k: topK,
      },
    });

    const results = res.data.items.map((item, index) => ({
      item: {
        id: String(item.run_id || `experiment-${index}`),
        partition: "experiments",
        title: String(item.run_id || `Experiment ${index + 1}`),
        content: JSON.stringify(item, null, 2),
        tags: ["experiments"],
        metadata: item,
        createdAt: nowIso(),
        updatedAt: nowIso(),
      },
      score: 0.8,
    }));

    return { results, total: res.data.count };
  },

  getFaultHistory: async (faultType: string, topK: number = 5) => {
    const res = await apiClient.get<FaultQueryResponse>("/api/knowledge/faults", {
      params: {
        fault_type: faultType,
        top_k: topK,
      },
    });

    const results = res.data.items.map((item, index) => ({
      item: {
        id: String(item.uri || `fault-${index}`),
        partition: "faults",
        title: titleFromUri(typeof item.uri === "string" ? item.uri : undefined, `Fault ${index + 1}`),
        content: typeof item.content === "string" ? item.content : JSON.stringify(item, null, 2),
        tags: ["faults"],
        metadata: item,
        createdAt: nowIso(),
        updatedAt: nowIso(),
      },
      score: typeof item.score === "number" ? item.score : 0.7,
    }));

    return { results, total: res.data.count };
  },
};
