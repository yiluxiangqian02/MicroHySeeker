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
}

interface BackendChatMessage {
  id: string;
  role: string;
  content: string;
  timestamp: string;
  agent_type?: string | null;
}

interface BackendChatResponse {
  status: string;
  session_id: string;
  intent: string;
  message: BackendChatMessage;
  data?: {
    reply?: string;
    intent?: string;
    sources?: string[];
  };
}

interface BackendChatHistoryResponse {
  messages: BackendChatMessage[];
  total: number;
  session_id: string;
}

const DEFAULT_SESSION_ID = "default";

const toChatMessagePayload = (message: BackendChatMessage): ChatMessagePayload => ({
  id: message.id,
  role: message.role === "assistant" ? "agent" : message.role === "user" ? "user" : "system",
  content: message.content,
  timestamp: message.timestamp,
  agentId: message.agent_type ?? undefined,
});

export const chatApi = {
  getDefaultSession: async (): Promise<ChatSession> => {
    const history = await chatApi.getMessages(DEFAULT_SESSION_ID);
    const lastMessage = history[history.length - 1];
    return {
      id: DEFAULT_SESSION_ID,
      title: "Default Conversation",
      updatedAt: lastMessage?.timestamp ?? new Date().toISOString(),
    };
  },

  getMessages: async (sessionId: string = DEFAULT_SESSION_ID) => {
    const res = await apiClient.get<BackendChatHistoryResponse>("/api/chat/history", {
      params: { session_id: sessionId },
    });
    return res.data.messages.map(toChatMessagePayload);
  },

  sendMessage: async (
    content: string,
    history: ChatMessagePayload[],
    sessionId: string = DEFAULT_SESSION_ID,
  ) => {
    const res = await apiClient.post<BackendChatResponse>("/api/chat", {
      session_id: sessionId,
      message: content,
      history: history.map((item) => ({
        id: item.id,
        role: item.role === "agent" ? "assistant" : item.role,
        content: item.content,
        timestamp: item.timestamp,
        agent_type: item.agentId,
      })),
    });
    return {
      ...res.data,
      message: toChatMessagePayload(res.data.message),
    };
  },

  analyzeExperiment: async (
    experimentId: string,
    message: string = "请分析此实验的响应情况",
  ) => {
    const res = await apiClient.post<BackendChatResponse>("/api/chat", {
      session_id: DEFAULT_SESSION_ID,
      message,
      experiment_id: experimentId,
    });
    return {
      ...res.data,
      message: res.data.data?.reply || res.data.message.content,
    };
  },
};

export { DEFAULT_SESSION_ID };
