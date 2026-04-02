"use client";

import { memo } from "react";
import { PolicyPreview } from "@/components/policy-preview";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  message: ChatMessage;
  currency: string;
}

export const ChatMessageBubble = memo(function ChatMessageBubble({ message, currency }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] space-y-2 rounded-lg px-3 py-2 text-base",
          isUser
            ? "bg-muted-foreground/15 text-foreground"
            : "bg-muted text-foreground",
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.policy_preview && (
          <PolicyPreview policy={message.policy_preview} currency={currency} />
        )}
      </div>
    </div>
  );
});
