import Link from "next/link";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiEndpoints } from "@/components/api-endpoints";
import { PublicNav } from "@/components/public-nav";
import { SupportLink } from "@/components/support-link";
import { PlaygroundSection } from "@/components/playground-link";
import { VersionLink } from "@/components/version-link";

export default function DevelopersPage() {
  return (
    <div className="min-h-screen bg-background">
      <PublicNav />

      <div className="mx-auto max-w-4xl px-4 py-12">
        <h1 className="text-3xl font-bold">Developer Documentation</h1>
        <p className="mt-2 text-muted-foreground">
          Integrate LetAgentPay with your AI agents in minutes.
        </p>

        {/* Quick Start */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold">Quick Start</h2>
          <ol className="mt-4 list-inside list-decimal space-y-3 text-base">
            <li>
              <Link href="/auth/signin" className="underline">
                Sign up
              </Link>{" "}
              with your email (magic link, no password)
            </li>
            <li>
              Create an agent in the dashboard and get your Bearer token (
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                agt_...
              </code>
              )
            </li>
            <li>Choose your integration method below and start sending requests</li>
          </ol>
          <PlaygroundSection />
        </section>

        {/* Authentication */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold">Authentication</h2>
          <p className="mt-2 text-base text-muted-foreground">
            All Agent API endpoints use Bearer token authentication:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-muted p-4 text-sm">
            <code>Authorization: Bearer agt_your_token_here</code>
          </pre>
        </section>

        {/* Integration Methods */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold">Integration</h2>
          <Tabs defaultValue="sdk" className="mt-4">
            <TabsList>
              <TabsTrigger value="sdk">Python SDK</TabsTrigger>
              <TabsTrigger value="mcp">MCP Server</TabsTrigger>
              <TabsTrigger value="rest">REST API</TabsTrigger>
            </TabsList>

            <TabsContent value="sdk" className="mt-4 space-y-4">
              <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
                <code>{`pip install letagentpay`}</code>
              </pre>
              <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
                <code>{`from letagentpay import LetAgentPay

client = LetAgentPay(token="agt_your_token")

# Submit a purchase request
result = client.purchase(
    amount=49.99,
    category="groceries",
    merchant_name="Whole Foods",
    description="Weekly groceries",
)

if result.status == "auto_approved":
    client.confirm(result.request_id, success=True, actual_amount=47.50)
elif result.status == "pending":
    final = client.wait_for_decision(result.request_id, timeout=300)
    if final.status == "approved":
        client.confirm(result.request_id, success=True)
elif result.status == "rejected":
    print(f"Rejected: {result.policy_check}")`}</code>
              </pre>

              <h3 className="font-semibold">Decorator Pattern</h3>
              <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
                <code>{`from letagentpay import LetAgentPay, guard

client = LetAgentPay(token="agt_your_token")

@guard(client, category="groceries")
def buy_groceries(items: list[str]) -> dict:
    total = calculate_total(items)
    return {"items": items, "total": total}`}</code>
              </pre>
            </TabsContent>

            <TabsContent value="mcp" className="mt-4 space-y-4">
              <h3 className="font-semibold">Claude Desktop</h3>
              <p className="text-base text-muted-foreground">
                Add to{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                  claude_desktop_config.json
                </code>
                :
              </p>
              <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
                <code>{`{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "@anthropic/letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_your_token"
      }
    }
  }
}`}</code>
              </pre>

              <h3 className="font-semibold">Cursor</h3>
              <p className="text-base text-muted-foreground">
                Add to{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                  .cursor/mcp.json
                </code>
                :
              </p>
              <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
                <code>{`{
  "mcpServers": {
    "letagentpay": {
      "command": "npx",
      "args": ["-y", "@anthropic/letagentpay-mcp"],
      "env": {
        "LETAGENTPAY_TOKEN": "agt_your_token"
      }
    }
  }
}`}</code>
              </pre>

              <p className="text-base text-muted-foreground">
                Available tools:{" "}
                <code className="text-xs">purchase_request</code>,{" "}
                <code className="text-xs">check_request_status</code>,{" "}
                <code className="text-xs">confirm_purchase</code>,{" "}
                <code className="text-xs">get_budget</code>,{" "}
                <code className="text-xs">get_policy</code>,{" "}
                <code className="text-xs">list_categories</code>
              </p>
            </TabsContent>

            <TabsContent value="rest" className="mt-4 space-y-4">
              <pre className="overflow-x-auto rounded-lg bg-muted p-4 text-sm">
                <code>{`# Create purchase request
curl -X POST https://letagentpay.com/api/v1/agent-api/requests \\
  -H "Authorization: Bearer agt_your_token" \\
  -H "Content-Type: application/json" \\
  -d '{"amount": 49.99, "category": "groceries", "merchant_name": "Whole Foods"}'

# Check status
curl https://letagentpay.com/api/v1/agent-api/requests/{request_id} \\
  -H "Authorization: Bearer agt_your_token"

# Confirm purchase
curl -X POST https://letagentpay.com/api/v1/agent-api/requests/{request_id}/confirm \\
  -H "Authorization: Bearer agt_your_token" \\
  -H "Content-Type: application/json" \\
  -d '{"success": true, "actual_amount": 47.50}'

# Get budget
curl https://letagentpay.com/api/v1/agent-api/budget \\
  -H "Authorization: Bearer agt_your_token"`}</code>
              </pre>
            </TabsContent>
          </Tabs>
        </section>

        {/* Framework Integrations */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold">Framework Integrations</h2>
          <p className="mt-2 text-base text-muted-foreground">
            LetAgentPay works with popular AI agent frameworks. Each integration
            wraps the Python SDK as a native tool for the framework.
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border p-4">
              <h3 className="font-semibold">LangChain</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Custom <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">BaseTool</code> for
                any LangChain agent.
              </p>
              <pre className="mt-2 overflow-x-auto rounded bg-muted p-3 text-xs">
                <code>{`from letagentpay_langchain import LetAgentPayTool

tool = LetAgentPayTool()
agent = create_tool_calling_agent(llm, [tool], prompt)`}</code>
              </pre>
              <a
                href="https://github.com/LetAgentPay/letagentpay/blob/main/examples/langchain_tool.py"
                className="mt-2 inline-block text-xs text-primary underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Full example
              </a>
            </div>
            <div className="rounded-lg border p-4">
              <h3 className="font-semibold">OpenAI Agents SDK</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Function tool with <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">@function_tool</code>.
              </p>
              <pre className="mt-2 overflow-x-auto rounded bg-muted p-3 text-xs">
                <code>{`@function_tool
def request_purchase(amount, category, ...):
    return client.request_purchase(...)`}</code>
              </pre>
              <a
                href="https://github.com/LetAgentPay/letagentpay/blob/main/examples/openai_agents.py"
                className="mt-2 inline-block text-xs text-primary underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Full example
              </a>
            </div>
            <div className="rounded-lg border p-4">
              <h3 className="font-semibold">CrewAI</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                CrewAI tool with <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">@tool</code> decorator.
              </p>
              <pre className="mt-2 overflow-x-auto rounded bg-muted p-3 text-xs">
                <code>{`@tool("Request Purchase")
def request_purchase(amount, category, ...):
    return client.request_purchase(...)`}</code>
              </pre>
              <a
                href="https://github.com/LetAgentPay/letagentpay/blob/main/examples/crewai_agent.py"
                className="mt-2 inline-block text-xs text-primary underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Full example
              </a>
            </div>
            <div className="rounded-lg border p-4">
              <h3 className="font-semibold">Claude MCP</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Zero-code integration via MCP server.
              </p>
              <pre className="mt-2 overflow-x-auto rounded bg-muted p-3 text-xs">
                <code>{`"letagentpay": {
  "command": "npx",
  "args": ["letagentpay-mcp"],
  "env": {"LETAGENTPAY_TOKEN": "agt_..."}
}`}</code>
              </pre>
              <a
                href="https://github.com/LetAgentPay/letagentpay/blob/main/docs/mcp_server.md"
                className="mt-2 inline-block text-xs text-primary underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                Full guide
              </a>
            </div>
          </div>
        </section>

        {/* API Reference */}
        <section className="mt-12">
          <div className="flex items-baseline justify-between gap-4">
            <h2 className="text-2xl font-bold">API Reference</h2>
            <a
              href="/openapi.yaml"
              className="text-sm text-primary underline hover:no-underline"
            >
              OpenAPI spec
            </a>
          </div>
          <p className="mt-2 text-base text-muted-foreground">
            Base URL:{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
              https://letagentpay.com/api/v1/agent-api
            </code>
          </p>
          <div className="mt-4">
            <ApiEndpoints />
          </div>
        </section>

        {/* Request Lifecycle */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold">Request Lifecycle</h2>
          <ol className="mt-4 list-inside list-decimal space-y-2 text-base text-muted-foreground">
            <li>Agent sends POST /requests with amount, category, description</li>
            <li>
              Policy engine runs checks: status, category, per-request limit,
              schedule, daily/weekly/monthly limits, budget, account budget rules
            </li>
            <li>
              All checks pass + auto-approve criteria met → <strong>auto_approved</strong>
            </li>
            <li>
              All checks pass, no auto-approve → <strong>pending</strong> (human reviews)
            </li>
            <li>
              Any check fails → <strong>rejected</strong> (with detailed explanation)
            </li>
            <li>Pending requests expire after 30 minutes if not reviewed</li>
            <li>After approval, agent confirms with POST /requests/{"{id}"}/confirm</li>
          </ol>
        </section>

        {/* Machine-readable links */}
        <section className="mt-12 border-t pt-8">
          <h2 className="text-lg font-semibold">Machine-Readable Resources</h2>
          <ul className="mt-3 space-y-1 text-sm">
            <li>
              <a
                href="/llms.txt"
                className="text-primary underline hover:no-underline"
              >
                /llms.txt
              </a>{" "}
              — Brief overview for LLMs
            </li>
            <li>
              <a
                href="/llms-full.txt"
                className="text-primary underline hover:no-underline"
              >
                /llms-full.txt
              </a>{" "}
              — Full API reference for LLMs
            </li>
            <li>
              <a
                href="/openapi.yaml"
                className="text-primary underline hover:no-underline"
              >
                /openapi.yaml
              </a>{" "}
              — OpenAPI 3.1 specification
            </li>
          </ul>
        </section>
      </div>

      <footer className="border-t py-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 text-sm text-muted-foreground">
          <span>
            LetAgentPay &copy; {new Date().getFullYear()}
            <VersionLink className="ml-2 text-xs opacity-40" />
          </span>
          <div className="flex gap-4">
            <Link href="/about" className="hover:text-foreground">
              About
            </Link>
            <Link href="/developers" className="hover:text-foreground">
              Developers
            </Link>
            <SupportLink className="hover:text-foreground" />
          </div>
        </div>
      </footer>
    </div>
  );
}
