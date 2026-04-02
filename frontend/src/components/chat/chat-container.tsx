"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatMessageBubble } from "@/components/chat/chat-message";
import { ChatInput } from "@/components/chat/chat-input";
import type { ChatMessage } from "@/lib/types";

interface ChatContainerProps {
  messages: ChatMessage[];
  currency: string;
  onSend: (message: string) => void;
  loading?: boolean;
}

export function ChatContainer({ messages, currency, onSend, loading }: ChatContainerProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-[50vh] sm:h-[60vh]">
      <ScrollArea className="flex-1 px-2">
        <div className="space-y-3 py-4">
          {messages.map((msg, i) => (
            <ChatMessageBubble key={i} message={msg} currency={currency} />
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-lg px-3 py-2 text-sm text-muted-foreground">
                Thinking...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>
      <div className="border-t pt-3">
        <ChatInput onSend={onSend} disabled={loading} />
      </div>
    </div>
  );
}
