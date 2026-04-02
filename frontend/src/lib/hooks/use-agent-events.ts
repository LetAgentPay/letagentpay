"use client";

import { useEffect, useRef } from "react";

// SSE must connect directly to the backend — Next.js dev server (Turbopack)
// buffers streaming responses when proxied through rewrites.
const SSE_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

type EventHandler = (event: { type: string; data: Record<string, unknown> }) => void;

export function useAgentEvents(agentId: string | null, onEvent: EventHandler) {
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    if (!agentId) return;

    const es = new EventSource(`${SSE_URL}/agents/${agentId}/events`, {
      withCredentials: true,
    });

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        handlerRef.current(data);
      } catch {
        // ignore parse errors
      }
    };

    return () => es.close();
  }, [agentId]);
}
