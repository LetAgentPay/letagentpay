import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Developers",
  description:
    "Integrate LetAgentPay with your AI agents via Python SDK, MCP Server, or REST API.",
};

export default function DevelopersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
