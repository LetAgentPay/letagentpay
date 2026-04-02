import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/lib/auth-context";
import { ServiceWorkerRegister } from "@/components/sw-register";
import { PushSubscribe } from "@/components/push-subscribe";
import { PWAInstallPrompt } from "@/components/pwa-install-prompt";
import { EEProvider } from "@/lib/ee-hooks";
import { PublicConfigProvider } from "@/components/public-config-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://letagentpay.com";

export const metadata: Metadata = {
  title: {
    default: "LetAgentPay — Control AI Agent Spending",
    template: "%s | LetAgentPay",
  },
  description:
    "Set budgets, define spending policies in plain English, and approve or reject AI agent purchases in real time.",
  metadataBase: new URL(siteUrl),
  manifest: "/manifest.json",
  keywords: [
    "AI agent",
    "spending management",
    "budget control",
    "AI policy",
    "purchase approval",
  ],
  authors: [{ name: "LetAgentPay" }],
  openGraph: {
    type: "website",
    siteName: "LetAgentPay",
    title: "LetAgentPay — Control AI Agent Spending",
    description:
      "Set budgets, define spending policies in plain English, and approve or reject AI agent purchases in real time.",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "LetAgentPay — Control AI Agent Spending",
    description:
      "Set budgets, define spending policies in plain English, and approve or reject AI agent purchases in real time.",
  },
  robots: {
    index: true,
    follow: true,
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "LetAgentPay",
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/icons/icon-192.png",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0a",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <link rel="llms" href="/llms.txt" />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "LetAgentPay",
              applicationCategory: "FinanceApplication",
              description:
                "AI agent spending management platform. Set budgets, define policies, approve purchases in real time.",
              url: siteUrl,
              operatingSystem: "Web",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "USD",
                description: "Free for early adopters",
              },
            }),
          }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <PublicConfigProvider>
          <AuthProvider>
            <EEProvider>{children}</EEProvider>
            <PushSubscribe />
          </AuthProvider>
        </PublicConfigProvider>
        <Toaster />
        <ServiceWorkerRegister />
        <PWAInstallPrompt />
      </body>
    </html>
  );
}
