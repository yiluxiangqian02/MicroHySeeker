import { create } from "zustand";
import { ChatSession, ChatMessagePayload } from "@/api/chat";

// Mock Data initially until Backend is wired
const MOCK_SESSIONS: ChatSession[] = [
  { id: "sess_1", title: "Analyze Exp-003-HER Outliers", updatedAt: new Date().toISOString() },
  { id: "sess_2", title: "General Knowledge Query", updatedAt: new Date(Date.now() - 3600000).toISOString() },
];

const MOCK_MESSAGES: Record<string, ChatMessagePayload[]> = {
  "sess_1": [
    { id: "m1", role: "system", content: "Context initialized for: Exp-003-HER Outliers.", timestamp: new Date(Date.now() - 7200000).toISOString() },
    { id: "m2", role: "user", content: "Can you analyze why there's a sudden voltage drop in step 4?", timestamp: new Date(Date.now() - 7000000).toISOString() },
    { id: "m3", role: "agent", agentId: "C1", content: "Based on the recorded e-chem data, the voltage drop in step 4 corresponds exactly to a temporary fluctuation in pump B's flow rate, leading to decreased reactant concentration. You can see this in the monitor logs.", timestamp: new Date(Date.now() - 6900000).toISOString() }
  ],
  "sess_2": [
    { id: "m4", role: "user", content: "What is the recommended range for catalyst concentration in HER?", timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: "m5", role: "agent", agentId: "C3", content: "According to the Knowledge Base (Viking), it's typically between **0.5 mg/cm² to 2.0 mg/cm²**, although recent high-yield experiments suggest pushing it near **1.5 mg/cm²**.", timestamp: new Date(Date.now() - 3500000).toISOString() }
  ]
};

interface ChatStore {
  sessions: ChatSession[];
  activeSessionId: string | null;
  messages: ChatMessagePayload[];
  isWaitingForResponse: boolean;

  fetchSessions: () => Promise<void>;
  setActiveSession: (id: string) => void;
  createNewSession: (title?: string) => void;
  sendMessage: (content: string, agentId?: string) => Promise<void>;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  isWaitingForResponse: false,

  fetchSessions: async () => {
    // API mock simulation
    await new Promise(resolve => setTimeout(resolve, 300));
    set({ sessions: MOCK_SESSIONS });
    if (!get().activeSessionId && MOCK_SESSIONS.length > 0) {
      get().setActiveSession(MOCK_SESSIONS[0].id);
    }
  },

  setActiveSession: (id: string) => {
    const sessionMsgs = MOCK_MESSAGES[id] || [];
    set({ activeSessionId: id, messages: sessionMsgs });
  },

  createNewSession: (title = "New Conversation") => {
    const newSession: ChatSession = {
      id: `sess_${Date.now()}`,
      title,
      updatedAt: new Date().toISOString()
    };
    MOCK_SESSIONS.unshift(newSession); // Store mock logic
    MOCK_MESSAGES[newSession.id] = [];
    
    set((state) => ({
      sessions: [newSession, ...state.sessions],
      activeSessionId: newSession.id,
      messages: []
    }));
  },

  sendMessage: async (content: string, agentId?: string) => {
    const { activeSessionId, messages } = get();
    if (!activeSessionId) return;

    const userMsg: ChatMessagePayload = {
      id: `m_${Date.now()}_u`,
      role: "user",
      content,
      timestamp: new Date().toISOString()
    };

    // Update optimistic UI
    const updatedMessages = [...messages, userMsg];
    set({ messages: updatedMessages, isWaitingForResponse: true });
    
    if(MOCK_MESSAGES[activeSessionId]) {
      MOCK_MESSAGES[activeSessionId].push(userMsg);
    }

    try {
      // Simulate API streaming/fetch delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const agentMsg: ChatMessagePayload = {
        id: `m_${Date.now()}_a`,
        role: "agent",
        agentId: agentId || "C2", // Default to supervisor if not specified
        content: `I've processed your request regarding: "${content}". Based on the current workspace context and agent capabilities, this looks like an area where I can assist further.`,
        timestamp: new Date().toISOString()
      };

      if(MOCK_MESSAGES[activeSessionId]) {
        MOCK_MESSAGES[activeSessionId].push(agentMsg);
      }
      set({ 
        messages: [...updatedMessages, agentMsg], 
        isWaitingForResponse: false 
      });
      
    } catch {
      set({ isWaitingForResponse: false });
    }
  }
}));
