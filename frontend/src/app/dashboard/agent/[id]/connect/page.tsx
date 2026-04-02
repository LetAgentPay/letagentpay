"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { api } from "@/lib/api";
import type { AgentResponse } from "@/lib/types";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

export default function ConnectPage() {
  const params = useParams();
  const agentId = params.id as string;
  const [agent, setAgent] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const loadAgent = useCallback(async () => {
    try {
      const data = await api.getAgent(agentId);
      setAgent(data);
    } catch {
      // Agent not found or error
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    loadAgent();
  }, [loadAgent]);

  function copyToken() {
    if (!agent) return;
    navigator.clipboard.writeText(agent.token);
    setCopied(true);
    toast.success("Token copied!");
    setTimeout(() => setCopied(false), 2000);
  }

  if (loading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!agent) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Agent not found</p>
      </div>
    );
  }

  const siteUrl =
    process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || `${siteUrl}/api/v1`;

  const curlExample = `curl -X POST ${apiUrl}/agent-api/requests \\
  -H "Authorization: Bearer ${agent.token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "amount": 25.00,
    "category": "groceries",
    "merchant_name": "SuperMart",
    "description": "Weekly groceries",
    "agent_comment": "Needed for meal prep this week"
  }'`;

  const pythonExample = `import requests

TOKEN = "${agent.token}"
API_URL = "${apiUrl}/agent-api"

# Request a purchase
resp = requests.post(
    f"{API_URL}/requests",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={
        "amount": 25.00,
        "category": "groceries",
        "merchant_name": "SuperMart",
        "description": "Weekly groceries",
        "agent_comment": "Needed for meal prep this week",
    },
)
print(resp.json())

# Check budget
budget = requests.get(
    f"{API_URL}/budget",
    headers={"Authorization": f"Bearer {TOKEN}"},
)
print(budget.json())`;

  const jsExample = `const TOKEN = "${agent.token}";
const API_URL = "${apiUrl}/agent-api";

// Request a purchase
const resp = await fetch(\`\${API_URL}/requests\`, {
  method: "POST",
  headers: {
    Authorization: \`Bearer \${TOKEN}\`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    amount: 25.0,
    category: "groceries",
    merchant_name: "SuperMart",
    description: "Weekly groceries",
    agent_comment: "Needed for meal prep this week",
  }),
});
console.log(await resp.json());`;

  const mcpConfig = `{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "${agent.token}"
      }
    }
  }
}`;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Connect: {agent.name}</h2>
        <Link href="/dashboard">
          <Button variant="outline" size="sm">
            Back
          </Button>
        </Link>
      </div>

      {/* Token */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Agent Token</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-muted px-3 py-2 text-sm break-all">
              {agent.token}
            </code>
            <Button
              variant="outline"
              size="icon"
              className="shrink-0"
              onClick={copyToken}
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Keep this token secret. It grants full access to this agent&apos;s API.
          </p>
        </CardContent>
      </Card>

      {/* Connection methods */}
      <Tabs defaultValue="curl">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="curl">curl</TabsTrigger>
          <TabsTrigger value="python">Python</TabsTrigger>
          <TabsTrigger value="js">JavaScript</TabsTrigger>
          <TabsTrigger value="mcp">MCP</TabsTrigger>
        </TabsList>

        <TabsContent value="curl">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Test with curl</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
                {curlExample}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="python">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Python</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
                {pythonExample}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="js">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">JavaScript / Node.js</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
                {jsExample}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mcp">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                MCP (Model Context Protocol)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Add this to your Claude Desktop or compatible MCP client
                configuration:
              </p>
              <pre className="overflow-x-auto rounded bg-muted p-4 text-xs">
                {mcpConfig}
              </pre>
              <p className="text-sm text-muted-foreground">
                Available tools: <code>request_purchase</code>,{" "}
                <code>check_budget</code>, <code>list_categories</code>,{" "}
                <code>my_requests</code>
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* API reference */}
      <Card>
        <CardContent className="py-4">
          <h3 className="font-medium mb-2">API Endpoints</h3>
          <div className="text-sm space-y-1 text-muted-foreground">
            <p>
              <code className="text-foreground">POST /agent-api/requests</code>{" "}
              — Create a purchase request
            </p>
            <p>
              <code className="text-foreground">
                GET /agent-api/requests/&#123;id&#125;
              </code>{" "}
              — Check request status
            </p>
            <p>
              <code className="text-foreground">
                POST /agent-api/requests/&#123;id&#125;/confirm
              </code>{" "}
              — Confirm purchase result
            </p>
            <p>
              <code className="text-foreground">GET /agent-api/budget</code> —
              Check remaining budget
            </p>
            <p>
              <code className="text-foreground">GET /agent-api/policy</code> —
              View current policy
            </p>
            <p>
              <code className="text-foreground">GET /agent-api/categories</code>{" "}
              — List valid categories
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
