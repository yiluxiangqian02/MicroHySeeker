import { apiClient } from "./client";

export interface KnowledgeItem {
  id: string;
  partition: string;
  title: string;
  content: string;
  tags: string[];
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface KnowledgeSearchRequest {
  query: string;
  partitions?: string[];
  limit?: number;
  minScore?: number;
}

export interface KnowledgeSearchResponse {
  results: Array<{
    item: KnowledgeItem;
    score: number;
  }>;
  total: number;
  partitionCounts?: Record<string, number>;
}

export const knowledgeApi = {
  /** 搜索知识库 */
  search: async (req: KnowledgeSearchRequest) => {
    const res = await apiClient.post<KnowledgeSearchResponse>("/api/knowledge/search", req);
    return res.data;
  },

  /** 获取最近录入的知识点（列表） */
  getRecent: async (limit: number = 10, partition?: string) => {
    const res = await apiClient.get<KnowledgeItem[]>("/api/knowledge/recent", {
      params: { limit, partition }
    });
    return res.data;
  },

  /** 获取单条知识详情 */
  getById: async (id: string) => {
    const res = await apiClient.get<KnowledgeItem>(`/api/knowledge/items/${id}`);
    return res.data;
  },

  /** 摄入/上传新的知识条目 */
  ingest: async (item: Partial<KnowledgeItem>) => {
    const res = await apiClient.post<{ ok: boolean; id: string }>("/api/knowledge/ingest", item);
    return res.data;
  }
};
