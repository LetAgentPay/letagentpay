/** Canonical site URL (used in metadata, llms.txt, etc.) */
export const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://letagentpay.com";

/** Whether running in self-hosted mode */
export const IS_SELF_HOSTED =
  process.env.NEXT_PUBLIC_SELF_HOSTED === "true";

