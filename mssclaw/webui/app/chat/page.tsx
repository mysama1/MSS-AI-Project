// mssclaw WebUI — Chat Page
// 吸收模式:
//   LobeChat: topic-based conversation, plugin gateway, streaming
//   NextChat: markdown rendering, model switching, local storage sessions

"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/components/chat-message";
import { ChatInput } from "@/components/chat-input";
import { ModelSelector } from "@/components/model-selector";
import { TopicList } from "@/components/topic-list";
import { useChatStore } from "@/lib/store";

export default function ChatPage() {
  const {
    messages,
    topics,
    currentTopic,
    streaming,
    sendMessage,
    switchTopic,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 吸收自 LobeChat: auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-4">
      {/* 吸收自 LobeChat: Topic sidebar */}
      <aside className="hidden w-56 shrink-0 lg:block">
        <TopicList
          topics={topics}
          currentTopic={currentTopic}
          onSwitch={switchTopic}
        />
      </aside>

      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        {/* 吸收自 NextChat: Model selector in header */}
        <div className="flex items-center justify-between border-b pb-3">
          <h2 className="text-lg font-semibold">
            {currentTopic?.title || "New Chat"}
          </h2>
          <ModelSelector />
        </div>

        {/* 吸收自 NextChat: Message list with markdown */}
        <div className="flex-1 overflow-y-auto py-4">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <p>Ask anything — mssclaw is ready.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 吸收自 LobeChat: Chat input with plugin gateway */}
        <div className="border-t pt-3">
          <ChatInput onSend={sendMessage} disabled={streaming} />
        </div>
      </div>
    </div>
  );
}
