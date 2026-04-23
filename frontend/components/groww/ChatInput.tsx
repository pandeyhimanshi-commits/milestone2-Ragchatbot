"use client";

import { useState } from "react";
import { Paperclip, Mic, Image, Send } from "lucide-react";

type ChatInputProps = {
  onSend: (message: string) => Promise<void> | void;
  isSending?: boolean;
};

export function ChatInput({ onSend, isSending = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const submit = async () => {
    const text = value.trim();
    if (!text || isSending) {
      return;
    }
    setValue("");
    await onSend(text);
  };

  return (
    <div className="w-full max-w-4xl">
      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-[var(--shadow-lg)]">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
          rows={3}
          placeholder="Type your investment query here..."
          className="w-full resize-none border-0 bg-transparent px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-0"
        />
        <div className="flex items-center justify-between border-t border-gray-100 px-3 py-2">
          <div className="flex items-center gap-0.5">
            <button
              type="button"
              className="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700"
              aria-label="Attach"
            >
              <Paperclip className="h-4 w-4" strokeWidth={2} />
            </button>
            <button
              type="button"
              className="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700"
              aria-label="Voice"
            >
              <Mic className="h-4 w-4" strokeWidth={2} />
            </button>
            <button
              type="button"
              className="rounded-lg p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700"
              aria-label="Image"
            >
              <Image className="h-4 w-4" strokeWidth={2} />
            </button>
          </div>
          <button
            type="button"
            onClick={() => void submit()}
            disabled={isSending || !value.trim()}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#00d09c] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00c090]"
          >
            {isSending ? "Sending..." : "Send"}
            <Send className="h-3.5 w-3.5" strokeWidth={2.5} />
          </button>
        </div>
      </div>
      <p className="mt-3 text-center text-[11px] leading-relaxed text-gray-400">
        Groww Assistant can provide financial information but always consult a professional advisor
        before investing.
      </p>
    </div>
  );
}
