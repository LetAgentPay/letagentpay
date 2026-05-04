"""Typed response models for LetAgentPay API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicyCheck:
    """Individual policy check result."""

    rule: str
    result: str  # "pass" | "fail"
    detail: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyCheck:
        return cls(rule=data["rule"], result=data["result"], detail=data["detail"])


@dataclass
class PolicyResult:
    """Aggregated policy check result."""

    passed: bool
    checks: list[PolicyCheck] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyResult:
        return cls(
            passed=data["passed"],
            checks=[PolicyCheck.from_dict(c) for c in data.get("checks", [])],
        )


@dataclass
class PurchaseResult:
    """Response from creating a purchase request."""

    request_id: str
    status: str  # "auto_approved" | "pending" | "rejected"
    currency: str | None = None
    category: str | None = None
    original_category: str | None = None
    policy_check: PolicyResult | None = None
    auto_approved: bool = False
    budget_remaining: float | None = None
    expires_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PurchaseResult:
        policy_check = None
        if data.get("policy_check"):
            policy_check = PolicyResult.from_dict(data["policy_check"])
        budget_remaining = data.get("budget_remaining")
        if budget_remaining is not None:
            budget_remaining = float(budget_remaining)
        return cls(
            request_id=data["request_id"],
            status=data["status"],
            currency=data.get("currency"),
            category=data.get("category"),
            original_category=data.get("original_category"),
            policy_check=policy_check,
            auto_approved=data.get("auto_approved", False),
            budget_remaining=budget_remaining,
            expires_at=data.get("expires_at"),
        )


@dataclass
class RequestStatus:
    """Response from checking a purchase request status."""

    request_id: str
    status: str
    amount: float
    category: str
    created_at: str
    reviewed_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RequestStatus:
        return cls(
            request_id=data["request_id"],
            status=data["status"],
            amount=float(data["amount"]),
            category=data["category"],
            created_at=str(data["created_at"]),
            reviewed_at=str(data["reviewed_at"]) if data.get("reviewed_at") else None,
        )


@dataclass
class ConfirmResult:
    """Response from confirming a purchase."""

    request_id: str
    status: str  # "completed" | "failed"
    actual_amount: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfirmResult:
        actual_amount = data.get("actual_amount")
        if actual_amount is not None:
            actual_amount = float(actual_amount)
        return cls(
            request_id=data["request_id"],
            status=data["status"],
            actual_amount=actual_amount,
        )


@dataclass
class BudgetInfo:
    """Current budget information."""

    budget: float
    spent: float
    held: float
    remaining: float
    currency: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BudgetInfo:
        return cls(
            budget=float(data["budget"]),
            spent=float(data["spent"]),
            held=float(data["held"]),
            remaining=float(data["remaining"]),
            currency=data.get("currency"),
        )


@dataclass
class PurchaseRequestInfo:
    """Purchase request in a list response."""

    request_id: str
    status: str
    amount: float
    currency: str
    category: str
    merchant: str | None = None
    description: str | None = None
    created_at: str | None = None
    reviewed_at: str | None = None
    expires_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PurchaseRequestInfo:
        return cls(
            request_id=data["request_id"],
            status=data["status"],
            amount=float(data["amount"]),
            currency=data.get("currency", "USD"),
            category=data.get("category", ""),
            merchant=data.get("merchant"),
            description=data.get("description"),
            created_at=str(data["created_at"]) if data.get("created_at") else None,
            reviewed_at=(
                str(data["reviewed_at"]) if data.get("reviewed_at") else None
            ),
            expires_at=str(data["expires_at"]) if data.get("expires_at") else None,
        )


@dataclass
class RequestList:
    """Paginated list of purchase requests."""

    requests: list[PurchaseRequestInfo]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RequestList:
        return cls(
            requests=[
                PurchaseRequestInfo.from_dict(r) for r in data.get("requests", [])
            ],
            total=data.get("total", 0),
            limit=data.get("limit", 20),
            offset=data.get("offset", 0),
        )


# --- x402 models ---


@dataclass
class X402AuthorizeResult:
    """Response from x402 authorize."""

    authorized: bool
    authorization_id: str | None = None
    reason: str | None = None
    expires_at: str | None = None
    remaining_daily_budget: float | None = None
    remaining_monthly_budget: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> X402AuthorizeResult:
        return cls(
            authorized=data["authorized"],
            authorization_id=data.get("authorization_id"),
            reason=data.get("reason"),
            expires_at=data.get("expires_at"),
            remaining_daily_budget=(
                float(data["remaining_daily_budget"])
                if data.get("remaining_daily_budget") is not None
                else None
            ),
            remaining_monthly_budget=(
                float(data["remaining_monthly_budget"])
                if data.get("remaining_monthly_budget") is not None
                else None
            ),
        )


@dataclass
class X402ReportResult:
    """Response from x402 report."""

    recorded: bool
    transaction_id: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> X402ReportResult:
        return cls(recorded=data["recorded"], transaction_id=data["transaction_id"])


@dataclass
class X402WalletInfo:
    """Agent wallet information."""

    wallet_address: str
    chain: str
    wallet_provider: str | None = None
    is_active: bool = True
    created_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> X402WalletInfo:
        return cls(
            wallet_address=data["wallet_address"],
            chain=data["chain"],
            wallet_provider=data.get("wallet_provider"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
        )
