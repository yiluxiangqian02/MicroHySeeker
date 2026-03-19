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
  /** 获取用户的对话会话历史列表 */
  getSessions: async () => {
    const res = await apiClient.get<ChatSession[]>("/api/chat/sessions");
    return res.data;
  },

  /** 获取指定会话中的消息记录 */
  getMessages: async (sessionId: string) => {
    const res = await apiClient.get<ChatMessagePayload[]>(`/api/chat/sessions/${sessionId}/messages`);
    return res.data;
  },

  /** 创建一个新的对话会话 */
  createSession: async (title: string, contextParams?: Record<string, any>) => {
    const res = await apiClient.post<ChatSession>("/api/chat/sessions", { title, contextParams });
    return res.data;
  },

  /** 
   * 发送消息并获取非流式的 Agent 结果
   * 如果后端支持 SSE，可以另写一个 useStreamChat hook 直接连接 /api/chat/stream 路由
   */
  sendMessage: async (sessionId: string, content: string, agentId?: string) => {
    const res = await apiClient.post<ChatMessagePayload>(`/api/chat/sessions/${sessionId}/messages`, {
      content,
      agentId
    });
    return res.data;
  }
};
