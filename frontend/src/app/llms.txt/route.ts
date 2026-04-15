export function GET() {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://letagentpay.com";

  const content = `# LetAgentPay

> AI agent spending management platform — policy middleware between AI agents and payments.

LetAgentPay lets humans define spending policies (budgets, category limits, schedules) for their AI agents. Agents send purchase requests via API; the platform validates them against policies and returns approve/reject decisions in real time. Multi-channel notifications (email, Telegram, browser push) let owners approve or reject requests from anywhere.

## Quick Start

1. Sign up at ${siteUrl}/auth/signin (magic link, no password)
2. Create an agent in the dashboard → get a Bearer token (agt_...)
3. Integrate via SDK, MCP Server, or REST API

## Integration Options

- **Python SDK**: \`pip install letagentpay\` — Python integration
- **TypeScript SDK**: \`npm install letagentpay\` — JS/TS integration
- **MCP Server**: \`npx letagentpay-mcp\` — Claude Desktop, Cursor, OpenClaw
- **REST API**: Direct HTTP calls for any language/framework
- **x402 Protocol**: Policy middleware for crypto-micropayments (USDC on Base)
- **LangChain**: Custom tool (BaseTool) — see examples/langchain_tool.py
- **OpenAI Agents SDK**: Function tool (@function_tool) — see examples/openai_agents.py
- **CrewAI**: CrewAI tool (@tool) — see examples/crewai_agent.py

## Links

- Full API reference: ${siteUrl}/llms-full.txt
- Developer docs: ${siteUrl}/developers
- OpenAPI spec: ${siteUrl}/api/v1/openapi.json
`;

  return new Response(content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
