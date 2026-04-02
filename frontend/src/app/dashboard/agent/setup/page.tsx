"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ChatContainer } from "@/components/chat/chat-container";
import { api, ApiError } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import { toast } from "sonner";
import { track } from "@/lib/ee-hooks";
import { useAuth } from "@/lib/auth-context";
import { Check } from "lucide-react";

function AgentSetupContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { currency } = useAuth();
  const agentId = searchParams.get("id");

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi! I'll help you set up a spending policy for your agent. Describe what rules you'd like — for example: limits per request, daily/weekly budgets, allowed categories, schedules, or auto-approve rules.",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [hasPreview, setHasPreview] = useState(false);

  if (!agentId) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No agent ID provided</p>
      </div>
    );
  }

  async function handleSend(message: string) {
    const userMsg: ChatMessage = { role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    // Build chat history for iterative refinement
    const chatHistory = messages
      .filter((m) => m.role === "user" || (m.role === "assistant" && !m.policy_preview))
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const result = await api.aiPolicyPreview(agentId!, message, chatHistory);
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: result.explanation,
        policy_preview: result.policy_preview,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setHasPreview(true);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.detail : "Failed to generate policy";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${detail}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    setLoading(true);
    try {
      await api.confirmAiPolicy(agentId!);
      track("policy_confirmed", { agent_id: agentId });
      toast.success("Policy confirmed!");
      const returnTo = searchParams.get("return");
      router.push(returnTo === "sandbox" ? "/dashboard/sandbox" : "/dashboard");
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.detail : "Failed to confirm policy",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Setup Policy</h2>
        {hasPreview && (
          <Button size="lg" onClick={handleConfirm} disabled={loading}>
            <Check className="mr-2 h-4 w-4" />
            Confirm Policy
          </Button>
        )}
      </div>
      <ChatContainer messages={messages} currency={currency} onSend={handleSend} loading={loading} />
    </div>
  );
}

export default function AgentSetupPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <AgentSetupContent />
    </Suspense>
  );
}
