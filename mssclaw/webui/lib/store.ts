// mssclaw WebUI — Zustand State Store
// 吸收模式: LobeChat (Zustand store pattern)

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
}

interface Topic {
  id: string;
  title: string;
  createdAt: number;
  messageCount: number;
}

interface ChatState {
  messages: Message[];
  topics: Topic[];
  currentTopic: Topic | null;
  streaming: boolean;
  selectedModel: string;

  sendMessage: (content: string) => void;
  switchTopic: (id: string) => void;
  setModel: (model: string) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      topics: [],
      currentTopic: null,
      streaming: false,
      selectedModel: "qwen2.5:7b",

      sendMessage: (content: string) => {
        const userMsg: Message = {
          id: crypto.randomUUID(),
          role: "user",
          content,
          timestamp: Date.now(),
        };
        set((s) => ({ messages: [...s.messages, userMsg], streaming: true }));

        // TODO: Replace with actual mssclaw agent API call
        setTimeout(() => {
          const reply: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: "This is a mock response. Connect to mssclaw agent server for real chat.",
            timestamp: Date.now(),
          };
          set((s) => ({
            messages: [...s.messages, reply],
            streaming: false,
          }));
        }, 1000);
      },

      switchTopic: (id: string) => {
        const topic = get().topics.find((t) => t.id === id);
        set({ currentTopic: topic || null });
      },

      setModel: (model: string) => {
        set({ selectedModel: model });
      },
    }),
    {
      name: "mssclaw-chat",
      partialize: (state) => ({
        topics: state.topics,
        selectedModel: state.selectedModel,
      }),
    }
  )
);
