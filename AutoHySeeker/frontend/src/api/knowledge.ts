import { apiClient } from "./client";

export interface KnowledgeItem {
  id: string;
  displayId?: string;
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
  payload?: Record<string, unknown>;
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

const clipText = (value: string, maxLen: number = 340) => {
  const compact = value.replace(/\s+/g, " ").trim();
  if (compact.length <= maxLen) {
    return compact;
  }
  return `${compact.slice(0, maxLen - 1)}…`;
};

const parsePaperIdFromUri = (uri?: string): string | undefined => {
  if (!uri) {
    return undefined;
  }
  const m = uri.match(/\/literature\/([^/]+)/i);
  return m?.[1];
};

const parseSeqFromRaw = (value: unknown): string | undefined => {
  if (typeof value !== "string") {
    return undefined;
  }
  const raw = value.trim();
  if (!raw) {
    return undefined;
  }
  const m = raw.match(/(?:-|_)?P(\d{1,6})$/i) || raw.match(/(\d{1,6})$/);
  if (!m) {
    return undefined;
  }
  return m[1].padStart(3, "0").slice(-3);
};

const parseSeqFromUri = (uri?: string): string | undefined => {
  if (!uri) {
    return undefined;
  }
  const m = uri.match(/\/P(\d{1,6})\.md$/i);
  return m?.[1]?.padStart(3, "0").slice(-3);
};

const paperTagNoHash = (paperId?: string): string | undefined => {
  if (!paperId) {
    return undefined;
  }
  const m = paperId.match(/^(\d{4})_([a-zA-Z]+)/);
  if (m) {
    return `${m[2].toUpperCase()}${m[1]}`;
  }
  return undefined;
};

const buildDisplayId = (
  item: KnowledgeSearchBackendItem,
  payload?: Record<string, unknown>,
): string | undefined => {
  const paperId =
    (typeof payload?.paper_id === "string" ? payload.paper_id : undefined) ||
    (typeof item.metadata?.paper_id === "string" ? item.metadata.paper_id : undefined) ||
    parsePaperIdFromUri(item.uri);
  const tag = paperTagNoHash(paperId);
  const seq =
    parseSeqFromRaw(payload?.paragraph_uid) ||
    parseSeqFromRaw(payload?.paragraph_id) ||
    parseSeqFromRaw(item.metadata?.paragraph_uid) ||
    parseSeqFromRaw(item.metadata?.paragraph_id) ||
    parseSeqFromUri(item.uri);
  if (!tag || !seq) {
    return undefined;
  }
  return `${tag}-P${seq}`;
};

const extractReadableContent = (
  rawContent: string | undefined,
  payload: Record<string, unknown>,
): string => {
  const candidates: unknown[] = [
    payload.paragraph_text,
    payload.text,
    payload.content,
    payload.abstract,
    payload.summary,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return clipText(candidate);
    }
  }

  if (rawContent) {
    const trimmed = rawContent.trim();
    if (!trimmed) {
      return "";
    }
    if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
      try {
        const parsed = JSON.parse(trimmed);
        return clipText(JSON.stringify(parsed, null, 2));
      } catch {
        return clipText(trimmed);
      }
    }
    return clipText(trimmed);
  }

  return "";
};

const toKnowledgeItem = (
  item: KnowledgeSearchBackendItem,
  partitionFallback: string,
): KnowledgeItem => {
  const timestamp = nowIso();
  const payload =
    item.payload && typeof item.payload === "object"
      ? item.payload
      : (() => {
          if (!item.content) {
            return {} as Record<string, unknown>;
          }
          try {
            const parsed = JSON.parse(item.content);
            return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : {};
          } catch {
            return {} as Record<string, unknown>;
          }
        })();
  const partition =
    typeof item.metadata?.partition === "string" ? item.metadata.partition : partitionFallback;
  const uri = typeof item.uri === "string" ? item.uri : undefined;
  const displayId = buildDisplayId(item, payload);
  const paperId =
    (typeof payload.paper_id === "string" ? payload.paper_id : undefined) ||
    (typeof item.metadata?.paper_id === "string" ? item.metadata.paper_id : undefined) ||
    parsePaperIdFromUri(uri);
  const headingText =
    (typeof payload.heading_text === "string" ? payload.heading_text : undefined) ||
    (typeof payload.original_heading === "string" ? payload.original_heading : undefined);
  const titleBase = titleFromUri(uri);
  const title = displayId
    ? headingText
      ? `${displayId} · ${headingText}`
      : displayId
    : titleBase;

  return {
    id: uri || `${partition}-${timestamp}`,
    displayId,
    partition,
    title,
    content: extractReadableContent(item.content, payload),
    tags: normalizeTags(item.metadata),
    metadata: {
      ...item.metadata,
      ...(paperId ? { paper_id: paperId } : {}),
      ...(headingText ? { heading_text: headingText } : {}),
      ...(typeof payload.paragraph_uid === "string" ? { paragraph_uid: payload.paragraph_uid } : {}),
      ...(typeof payload.paragraph_id === "string" ? { paragraph_id: payload.paragraph_id } : {}),
      ...(typeof payload.evidence_id === "string" ? { evidence_id: payload.evidence_id } : {}),
      ...(uri ? { uri } : {}),
    },
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

// ── MinerU Ingest API ─────────────────────────────────────────────────────────

export interface IngestRequest {
  mineru_output_dir?: string;
  target_uri?: string;
  batch_name?: string;
}

export interface IngestTask {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed" | "idle";
  mineru_dir?: string;
  target?: string;
  created_at?: number;
  started_at?: number;
  finished_at?: number;
  error?: string;
  result?: Record<string, unknown>;
}

export interface DefaultDirInfo {
  default_mineru_output: string;
  exists: boolean;
  document_count: number;
}

export const ingestApi = {
  startIngest: async (req: IngestRequest = {}): Promise<IngestTask> => {
    const res = await apiClient.post<IngestTask>("/api/knowledge/ingest-mineru", req);
    return res.data;
  },

  getStatus: async (taskId?: string): Promise<{ latest?: IngestTask; tasks?: IngestTask[]; total?: number; status?: string }> => {
    const res = await apiClient.get("/api/knowledge/ingest-status", {
      params: taskId ? { task_id: taskId } : undefined,
    });
    return res.data;
  },

  getDefaultDir: async (): Promise<DefaultDirInfo> => {
    const res = await apiClient.get<DefaultDirInfo>("/api/knowledge/ingest-default-dir");
    return res.data;
  },
};
