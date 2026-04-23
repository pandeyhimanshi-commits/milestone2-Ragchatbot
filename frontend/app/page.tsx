"use client";

import { useMemo, useState } from "react";
import { Sidebar } from "@/components/groww/Sidebar";
import { TopBar } from "@/components/groww/TopBar";
import { GreetingHeadline } from "@/components/groww/GreetingHeadline";
import { QuickActionGrid } from "@/components/groww/QuickActionGrid";
import { MarketSnapshot } from "@/components/groww/MarketSnapshot";
import { ProTip } from "@/components/groww/ProTip";
import { ChatInput } from "@/components/groww/ChatInput";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

type ChatThread = {
  id: string;
  title: string;
  messages: ChatMessage[];
};

function renderBotText(text: string) {
  const urlRe = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRe);
  return parts.map((part, idx) => {
    if (/^https?:\/\//i.test(part)) {
      return (
        <a
          key={`${part}-${idx}`}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="break-all text-[#00a884] underline"
        >
          {part}
        </a>
      );
    }
    return <span key={`txt-${idx}`}>{part}</span>;
  });
}

export default function Home() {
  const [threads, setThreads] = useState<ChatThread[]>(() => [
    {
      id: `web-${crypto.randomUUID()}`,
      title: "New Chat",
      messages: [{ role: "assistant", text: "How may I help you?" }],
    },
  ]);
  const [activeThreadId, setActiveThreadId] = useState(() => threads[0].id);
  const [isSending, setIsSending] = useState(false);
  const activeThread = useMemo(
    () => threads.find((t) => t.id === activeThreadId) ?? threads[0],
    [threads, activeThreadId],
  );
  const messages = activeThread?.messages ?? [];

  const hasOnlyWelcome = useMemo(
    () => messages.length === 1 && messages[0]?.role === "assistant",
    [messages],
  );

  const sendMessage = async (text: string) => {
    const tid = activeThread.id;
    setThreads((prev) =>
      prev.map((t) =>
        t.id === tid
          ? {
              ...t,
              title: t.title === "New Chat" ? text.slice(0, 32) : t.title,
              messages: [...t.messages, { role: "user", text }],
            }
          : t,
      ),
    );
    setIsSending(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: tid, message: text }),
      });
      const data = await res.json();
      const botText =
        data?.answer ||
        data?.error ||
        `Request failed${res.status ? ` (${res.status})` : ""}.`;
      setThreads((prev) =>
        prev.map((t) =>
          t.id === tid
            ? { ...t, messages: [...t.messages, { role: "assistant", text: String(botText) }] }
            : t,
        ),
      );
    } catch (err) {
      setThreads((prev) =>
        prev.map((t) =>
          t.id === tid
            ? {
                ...t,
                messages: [...t.messages, { role: "assistant", text: `Request failed: ${String(err)}` }],
              }
            : t,
        ),
      );
    } finally {
      setIsSending(false);
    }
  };

  const startNewChat = () => {
    if (isSending) {
      return;
    }
    const newThread: ChatThread = {
      id: `web-${crypto.randomUUID()}`,
      title: "New Chat",
      messages: [{ role: "assistant", text: "How may I help you?" }],
    };
    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(newThread.id);
  };

  const threadTabs = useMemo(
    () =>
      threads.map((t) => {
        const last = t.messages[t.messages.length - 1];
        return {
          id: t.id,
          title: t.title || "New Chat",
          preview: last?.text || "No messages yet",
        };
      }),
    [threads],
  );

  return (
    <div className="flex h-screen min-h-0 bg-[#f8f9fa] text-[var(--foreground)]">
      <Sidebar
        threads={threadTabs}
        activeThreadId={activeThread.id}
        onSelectThread={setActiveThreadId}
        onNewChat={startNewChat}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar />

        <div className="flex min-h-0 flex-1 gap-6 overflow-hidden p-6">
          <main className="flex min-h-0 min-w-0 flex-1 flex-col">
            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
              <div className="mx-auto flex w-full max-w-3xl flex-col px-1">
                <div className="flex flex-col items-center">
                  <GreetingHeadline />
                </div>

                <div className="mb-3 mt-2 space-y-3">
                  {messages.map((m, idx) => (
                    <div
                      key={`${m.role}-${idx}`}
                      className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={
                          m.role === "user"
                            ? "max-w-[80%] rounded-2xl rounded-br-sm bg-gradient-to-r from-[#00c896] to-[#00d09c] px-4 py-3 text-sm font-medium text-white shadow-md whitespace-pre-wrap"
                            : "max-w-[85%] rounded-2xl rounded-tl-sm border border-gray-100 bg-white px-4 py-3 text-sm text-gray-800 shadow-sm whitespace-pre-wrap"
                        }
                      >
                        {m.role === "assistant" ? renderBotText(m.text) : m.text}
                      </div>
                    </div>
                  ))}
                </div>

                {hasOnlyWelcome && (
                  <div className="flex justify-center">
                    <QuickActionGrid />
                  </div>
                )}

                {isSending && (
                  <div className="mb-2 mt-1 text-sm text-gray-500">Assistant is typing...</div>
                )}
              </div>
            </div>
            <div className="shrink-0 pt-4">
              <div className="mx-auto flex max-w-4xl justify-center px-2">
                <ChatInput onSend={sendMessage} isSending={isSending} />
              </div>
            </div>
          </main>

          <aside className="hidden w-[300px] shrink-0 flex-col gap-4 overflow-y-auto lg:flex">
            <MarketSnapshot />
            <ProTip />
          </aside>
        </div>
      </div>
    </div>
  );
}
