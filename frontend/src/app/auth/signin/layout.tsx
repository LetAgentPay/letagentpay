import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign In",
  description: "Sign in to LetAgentPay to manage your AI agent spending policies.",
  openGraph: {
    title: "Sign In | LetAgentPay",
    description: "Sign in to LetAgentPay to manage your AI agent spending policies.",
  },
};

export default function SignInLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
