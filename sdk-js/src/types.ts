/** Individual policy check result. */
export interface PolicyCheck {
  rule: string;
  result: "pass" | "fail";
  detail: string;
}

/** Aggregated policy check result. */
export interface PolicyResult {
  passed: boolean;
  checks: PolicyCheck[];
}

/** Response from creating a purchase request. */
export interface PurchaseResult {
  requestId: string;
  status: "auto_approved" | "pending" | "rejected";
  currency: string | null;
  category: string | null;
  originalCategory: string | null;
  policyCheck: PolicyResult | null;
  autoApproved: boolean;
  budgetRemaining: number | null;
  expiresAt: string | null;
}

/** Response from checking a purchase request status. */
export interface RequestStatus {
  requestId: string;
  status: string;
  amount: number;
  category: string;
  createdAt: string;
  reviewedAt: string | null;
}

/** Response from confirming a purchase. */
export interface ConfirmResult {
  requestId: string;
  status: "completed" | "failed";
  actualAmount: number | null;
}

/** Current budget information. */
export interface BudgetInfo {
  budget: number;
  spent: number;
  held: number;
  remaining: number;
  currency: string | null;
}

/** Purchase request in a list response. */
export interface PurchaseRequestInfo {
  requestId: string;
  status: string;
  amount: number;
  currency: string;
  category: string;
  merchant: string | null;
  description: string | null;
  createdAt: string | null;
  reviewedAt: string | null;
  expiresAt: string | null;
}

/** Paginated list of purchase requests. */
export interface RequestList {
  requests: PurchaseRequestInfo[];
  total: number;
  limit: number;
  offset: number;
}

/** Options for creating a purchase request. */
export interface PurchaseOptions {
  amount: number;
  category: string;
  merchantName?: string;
  description?: string;
  agentComment?: string;
}

/** Options for confirming a purchase. */
export interface ConfirmOptions {
  success: boolean;
  actualAmount?: number;
  receiptUrl?: string;
}

/** Options for listing requests. */
export interface ListRequestsOptions {
  status?: string;
  limit?: number;
  offset?: number;
}

/** Client configuration. */
export interface LetAgentPayConfig {
  token?: string;
  baseUrl?: string;
}

// --- x402 types ---

/** x402 payment requirements from HTTP 402 response. */
export interface X402PaymentRequirements {
  scheme: string;
  network: string;
  amount: string;
  asset: string;
  pay_to: string;
  resource?: string;
}

/** Options for x402 authorize request. */
export interface X402AuthorizeOptions {
  amountUsd: number;
  asset?: string;
  network?: string;
  payTo: string;
  resourceUrl?: string;
  category?: string;
}

/** Response from x402 authorize. */
export interface X402AuthorizeResult {
  authorized: boolean;
  authorizationId: string | null;
  reason: string | null;
  expiresAt: string | null;
  remainingDailyBudget: number | null;
  remainingMonthlyBudget: number | null;
}

/** Options for x402 report. */
export interface X402ReportOptions {
  authorizationId: string;
  txHash: string;
  actualAmountUsd?: number;
  resourceUrl?: string;
}

/** Response from x402 report. */
export interface X402ReportResult {
  recorded: boolean;
  transactionId: string;
}

/** Agent wallet info. */
export interface X402WalletInfo {
  walletAddress: string;
  chain: string;
  walletProvider: string | null;
  isActive: boolean;
  createdAt: string | null;
}

/** Options for registering a wallet. */
export interface X402RegisterWalletOptions {
  walletAddress: string;
  chain?: string;
  walletProvider?: string;
}
