import { apiClient } from "./client";

export interface ChatMessagePayload {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  timestamp: string;
  agentId?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  updatedAt: string;
  contextParams?: Record<string, any>;
}

export const chatApi = {
  getSessions: async () => {
    const res = await apiClient.get<ChatSession[]>("/api/chat/sessions");
    return res.data;
  },
  getMessages: async (sessionId: string) => {
    const res = await apiClient.get<ChatMessagePayload[]>(`/api/chat/sessions/${sessionId}/messages`);
    return res.data;
  },
  createSession: async (title: string, contextParams?: Record<string, any>) => {
    const res = await apiClient.post<ChatSession>("/api/chat/sessions", { title, contextParams });
    return res.data;
  },
  sendMessage: async (sessionId: string, content: string, agentId?: string) => {
    const res = await apiClient.post<ChatMessagePayload>(`/api/chat/sessions/${sessionId}/messages`, { content, agentId });
    return res.data;
  },
  analyzeExperiment: async (experimentId: string, message: string = "请分析此实验的响应情况") => {
    const res = await apiClient.post("/api/chat", {
      message,
      experiment_id: experimentId
    });
    return res.data;
  }
};
