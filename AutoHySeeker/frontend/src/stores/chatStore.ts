import { create } from "zustand";
import { ChatMessagePayload, ChatSession, DEFAULT_SESSION_ID, chatApi } from "@/api/chat";

interface ChatStore {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessagePayload[];
  isWaitingForResponse: boolean;
  error: string | null;
  fetchSessions: () => Promise<void>;
  setActiveSession: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isWaitingForResponse: false,
  error: null,

  fetchSessions: async () => {
    const messages = await chatApi.getMessages(DEFAULT_SESSION_ID);
    const lastMessage = messages[messages.length - 1];
    const session: ChatSession = {
      id: DEFAULT_SESSION_ID,
      title: "Default Conversation",
      updatedAt: lastMessage?.timestamp || new Date().toISOString(),
    };
    set({
      sessions: [session],
      activeSessionId: session.id,
      messages,
      error: null,
    });
  },

  setActiveSession: async (id: string) => {
    if (id !== DEFAULT_SESSION_ID) {
      return;
    }
    const messages = await chatApi.getMessages(id);
    set({ activeSessionId: id, messages, error: null });
  },

  sendMessage: async (content: string) => {
    const { activeSessionId, messages, sessions } = get();
    const sessionId = activeSessionId || DEFAULT_SESSION_ID;
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }

    const userMessage: ChatMessagePayload = {
      id: `local_${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    const optimisticHistory = [...messages, userMessage];
    set({
      activeSessionId: sessionId,
      messages: optimisticHistory,
      isWaitingForResponse: true,
      error: null,
    });

    try {
      const response = await chatApi.sendMessage(trimmed, messages, sessionId);
      const assistantMessage = response.message;
      const updatedAt = assistantMessage.timestamp || new Date().toISOString();

      set({
        sessions: [
          {
            id: sessionId,
            title: sessions[0]?.title || "Default Conversation",
            updatedAt,
          },
        ],
        messages: [...optimisticHistory, assistantMessage],
        isWaitingForResponse: false,
        error: null,
      });
    } catch (error) {
      set({
        messages,
        isWaitingForResponse: false,
        error: error instanceof Error ? error.message : "Failed to send message",
      });
      throw error;
    }
  },
}));
