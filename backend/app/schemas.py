from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator
from pydantic.functional_serializers import PlainSerializer


def _serialize_utc_datetime(v: datetime) -> str:
    """Serialize UTC datetimes with 'Z' suffix."""
    if v.tzinfo is None:
        v = v.replace(tzinfo=UTC)
    return v.isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_serialize_utc_datetime)]

VALID_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "CNY",
    "KRW",
    "INR",
    "BRL",
    "RUB",
    "TRY",
    "AUD",
    "CAD",
    "CHF",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "RON",
    "BGN",
    "HRK",
    "MXN",
    "ARS",
    "CLP",
    "COP",
    "PEN",
    "UYU",
    "ZAR",
    "EGP",
    "AED",
    "SAR",
    "ILS",
    "THB",
    "SGD",
    "HKD",
    "TWD",
    "NZD",
    "PHP",
    "IDR",
    "MYR",
    "VND",
    "NGN",
    "KES",
    "GHS",
    "UAH",
    "KZT",
    "GEL",
    "AMD",
}

VALID_SETTLEMENT_CURRENCIES = {"USDC", "USDT", "EURC"}

VALID_CHAINS = {"base", "base-sepolia", "ethereum", "solana"}

VALID_SETTLEMENT_METHODS = {"x402", "stripe", "manual"}

_VALID_TIMEZONES = available_timezones()


def validate_currency(v: str) -> str:
    v = v.upper().strip()
    if v not in VALID_CURRENCIES:
        raise ValueError(f"Unsupported currency: {v}")
    return v


def validate_timezone(v: str) -> str:
    if v not in _VALID_TIMEZONES:
        raise ValueError(f"Unknown timezone: {v}")
    return v


# --- Auth ---


class PasswordLoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=255)


class SendLinkRequest(BaseModel):
    email: str = Field(max_length=255)


class VerifyOtpRequest(BaseModel):
    email: str = Field(max_length=255)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    message: str


# --- Account ---


class AccountResponse(BaseModel):
    id: str
    email: str
    name: str | None
    currency: str
    timezone: str
    plan: str
    plan_price: Decimal = Decimal("0.00")
    billing_period: str = "monthly"
    is_admin: bool
    blocked: bool
    all_agents_paused: bool
    request_expiry_minutes: int
    created_at: UtcDatetime


class KillSwitchRequest(BaseModel):
    paused: bool


class UpdateAccountRequest(BaseModel):
    name: str | None = None
    currency: str | None = Field(None, max_length=3)
    timezone: str | None = Field(None, max_length=50)
    request_expiry_minutes: int | None = Field(None, ge=5, le=1440)

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_currency(v)
        return v

    @field_validator("timezone")
    @classmethod
    def check_timezone(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_timezone(v)
        return v


# --- Policy ---


class ScheduleOverride(BaseModel):
    days: list[str]
    daily_limit: Decimal | None = None
    allow: str | None = None
    deny: bool | None = None


class Schedule(BaseModel):
    timezone: str
    default: dict[str, str]
    overrides: list[ScheduleOverride] | None = None


class AutoApprove(BaseModel):
    enabled: bool
    max_amount: Decimal | None = None
    categories: list[str] | None = None


class Policy(BaseModel):
    daily_limit: Decimal | None = None
    weekly_limit: Decimal | None = None
    monthly_limit: Decimal | None = None
    per_request_limit: Decimal | None = None
    allowed_categories: list[str] | None = None
    blocked_categories: list[str] | None = None
    schedule: Schedule | None = None
    auto_approve: AutoApprove | None = None


# --- Budget ---


class AdjustBudgetRequest(BaseModel):
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("amount must not be zero")
        return v


class AutoReplenishRequest(BaseModel):
    threshold: Decimal = Field(gt=0)
    amount: Decimal = Field(gt=0)
    max_budget: Decimal | None = Field(None, gt=0)


class AutoReplenishResponse(BaseModel):
    enabled: bool
    threshold: Decimal | None = None
    amount: Decimal | None = None
    max_budget: Decimal | None = None


# --- Agent ---


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_sandbox: bool = False


class UpdateAgentRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    status: str
    is_sandbox: bool
    budget: Decimal
    spent: Decimal
    held: Decimal
    remaining: Decimal
    pending_count: int
    policy: dict | None
    policy_text: str | None
    token: str
    auto_replenish: AutoReplenishResponse | None = None
    created_at: UtcDatetime


class AgentBriefResponse(BaseModel):
    id: str
    name: str
    status: str
    budget: Decimal
    spent: Decimal
    held: Decimal


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]


# --- Policy AI ---


class PolicyAIRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    chat_history: list[dict] | None = None


class PolicyAIResponse(BaseModel):
    policy_preview: dict
    explanation: str
    session_id: str


# --- Purchase Request ---


class CreatePurchaseRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str | None = Field(None, max_length=3)
    category: str = Field(max_length=50)
    merchant_name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    agent_comment: str | None = Field(None, max_length=2000)

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_currency(v)
        return v


class PolicyCheckResult(BaseModel):
    rule: str
    result: str  # "pass" | "fail"
    detail: str


class PurchaseRequestResponse(BaseModel):
    request_id: str
    status: str
    currency: str | None = None
    category: str | None = None
    original_category: str | None = None
    policy_check: dict | None
    auto_approved: bool
    budget_remaining: Decimal | None = None
    expires_at: UtcDatetime | None = None


class PurchaseRequestListItem(BaseModel):
    id: str
    agent_id: str
    agent_name: str | None = None
    amount: Decimal
    category: str
    original_category: str | None = None
    merchant: str | None
    description: str | None
    agent_comment: str | None
    currency: str | None = None
    status: str
    rejection_reason: str | None = None
    actual_amount: Decimal | None
    receipt_url: str | None
    settlement_method: str | None = None
    settlement_currency: str | None = None
    tx_hash: str | None = None
    completed_at: UtcDatetime | None
    created_at: UtcDatetime
    reviewed_at: UtcDatetime | None


class ConfirmPurchaseRequest(BaseModel):
    success: bool
    actual_amount: Decimal | None = None
    receipt_url: str | None = Field(None, max_length=2000)


class BudgetResponse(BaseModel):
    budget: Decimal
    spent: Decimal
    held: Decimal
    remaining: Decimal
    currency: str | None = None


# --- Push ---


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


# --- Budget Rules ---


class BudgetRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    limit_type: Literal["daily", "weekly", "monthly", "total"]
    limit_amount: Decimal = Field(gt=0)
    priority: int = Field(default=0, ge=0)
    days_of_week: list[int] | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class BudgetRuleResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    priority: int
    limit_type: str
    limit_amount: Decimal
    days_of_week: list[int] | None
    start_at: UtcDatetime | None
    end_at: UtcDatetime | None
    created_at: UtcDatetime
    spent: Decimal | None = None


class BudgetRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    limit_amount: Decimal | None = Field(None, gt=0)
    priority: int | None = Field(None, ge=0)
    is_active: bool | None = None
    days_of_week: list[int] | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class AccountBudgetResponse(BaseModel):
    account_spent: Decimal
    currency: str
    daily_spent: Decimal
    weekly_spent: Decimal
    monthly_spent: Decimal
    rules: list[BudgetRuleResponse]


class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int


# --- x402 ---


class X402PaymentRequirements(BaseModel):
    scheme: str = Field(max_length=20)
    network: str = Field(max_length=30)
    amount: str = Field(max_length=50)
    asset: str = Field(max_length=10)
    pay_to: str = Field(max_length=64)
    resource: str | None = Field(None, max_length=2000)


class X402AuthorizeRequest(BaseModel):
    payment_requirements: X402PaymentRequirements
    max_amount_usd: Decimal = Field(gt=0)
    category: str = Field(default="api", max_length=50)

    @field_validator("max_amount_usd")
    @classmethod
    def check_max_amount(cls, v: Decimal) -> Decimal:
        if v > 10000:
            raise ValueError("max_amount_usd cannot exceed 10000")
        return v


class X402AuthorizeResponse(BaseModel):
    authorized: bool
    authorization_id: str | None = None
    reason: str | None = None
    expires_at: UtcDatetime | None = None
    remaining_daily_budget: Decimal | None = None
    remaining_monthly_budget: Decimal | None = None


class X402ReportRequest(BaseModel):
    authorization_id: str = Field(max_length=36)
    tx_hash: str = Field(max_length=66)
    actual_amount: str | None = Field(None, max_length=50)
    actual_amount_usd: Decimal | None = Field(None, gt=0)
    resource_url: str | None = Field(None, max_length=2000)


class X402ReportResponse(BaseModel):
    recorded: bool
    transaction_id: str


class AgentWalletRequest(BaseModel):
    wallet_address: str = Field(min_length=1, max_length=64)
    chain: str = Field(max_length=20)
    wallet_provider: str | None = Field(None, max_length=50)

    @field_validator("chain")
    @classmethod
    def check_chain(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_CHAINS:
            raise ValueError(f"Unsupported chain: {v}")
        return v


class AgentWalletResponse(BaseModel):
    wallet_address: str
    chain: str
    wallet_provider: str | None
    is_active: bool
    created_at: UtcDatetime
