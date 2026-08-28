from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, StringConstraints, field_validator
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


class SignupAttribution(BaseModel):
    """Optional signup attribution captured client-side from UTM params or
    landing page. All fields nullable; ignored on existing accounts."""

    landing: str | None = Field(default=None, max_length=64)
    source: str | None = Field(default=None, max_length=64)
    medium: str | None = Field(default=None, max_length=64)
    campaign: str | None = Field(default=None, max_length=128)
    content: str | None = Field(default=None, max_length=128)


# Trim and lowercase first, then check the shape. Loose on purpose — this only
# has to reject garbage before it reaches Resend or the DB, and it saves pulling
# in email-validator for a single field.
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        max_length=255,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    ),
]


class SendLinkRequest(BaseModel):
    email: Email
    attribution: SignupAttribution | None = None


class VerifyOtpRequest(BaseModel):
    email: Email
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
    currency: str | None = Field(default=None, max_length=3)
    timezone: str | None = Field(default=None, max_length=50)
    request_expiry_minutes: int | None = Field(default=None, ge=5, le=1440)

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
    max_amount: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    categories: list[str] | None = None


class Policy(BaseModel):
    daily_limit: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    weekly_limit: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    monthly_limit: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    per_request_limit: Decimal | None = Field(default=None, ge=0, le=9_999_999)
    requests_per_minute: int | None = Field(default=None, ge=1, le=10_000)
    requests_per_hour: int | None = Field(default=None, ge=1, le=1_000_000)
    allowed_categories: list[str] | None = None
    blocked_categories: list[str] | None = None
    schedule: Schedule | None = None
    auto_approve: AutoApprove | None = None


# --- Budget ---


class AdjustBudgetRequest(BaseModel):
    amount: Decimal = Field(ge=-9_999_999, le=9_999_999)

    @field_validator("amount")
    @classmethod
    def not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("amount must not be zero")
        return v


class AutoReplenishRequest(BaseModel):
    threshold: Decimal = Field(gt=0, le=9_999_999)
    amount: Decimal = Field(gt=0, le=9_999_999)
    max_budget: Decimal | None = Field(default=None, gt=0, le=9_999_999)


class AutoReplenishResponse(BaseModel):
    enabled: bool
    threshold: Decimal | None = None
    amount: Decimal | None = None
    max_budget: Decimal | None = None


# --- Agent ---


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    is_sandbox: bool = False


class UpdateAgentRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


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
    amount: Decimal = Field(gt=0, le=9_999_999)
    currency: str | None = Field(default=None, max_length=3)
    category: str = Field(max_length=50)
    merchant_name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    agent_comment: str | None = Field(default=None, max_length=2000)

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
    actual_amount: Decimal | None = Field(default=None, gt=0, le=9_999_999)
    receipt_url: str | None = Field(default=None, max_length=2000)


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
    limit_amount: Decimal = Field(gt=0, le=9_999_999)
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
    name: str | None = Field(default=None, min_length=1, max_length=255)
    limit_amount: Decimal | None = Field(default=None, gt=0, le=9_999_999)
    priority: int | None = Field(default=None, ge=0)
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
    resource: str | None = Field(default=None, max_length=2000)


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
    # EVM tx hash: 0x + 64 hex chars (66 total)
    # Solana tx signature: 87-88 base58 chars
    tx_hash: str = Field(
        max_length=88,
        pattern=r"^(0x[0-9a-fA-F]{64}|[1-9A-HJ-NP-Za-km-z]{87,88})$",
    )
    actual_amount: str | None = Field(default=None, max_length=50)
    actual_amount_usd: Decimal | None = Field(default=None, gt=0)
    resource_url: str | None = Field(default=None, max_length=2000)


class X402ReportResponse(BaseModel):
    recorded: bool
    transaction_id: str


_EVM_ADDRESS_RE = r"^0x[0-9a-fA-F]{40}$"
_SOLANA_ADDRESS_RE = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"


class AgentWalletRequest(BaseModel):
    wallet_address: str = Field(min_length=1, max_length=64)
    chain: str = Field(max_length=20)
    wallet_provider: str | None = Field(default=None, max_length=50)

    @field_validator("chain")
    @classmethod
    def check_chain(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_CHAINS:
            raise ValueError(f"Unsupported chain: {v}")
        return v

    @field_validator("wallet_address")
    @classmethod
    def check_wallet_address(cls, v: str, info) -> str:
        import re

        v = v.strip()
        chain = (info.data.get("chain") or "").lower().strip()
        if chain == "solana":
            if not re.match(_SOLANA_ADDRESS_RE, v):
                raise ValueError("Invalid Solana address format")
        else:
            if not re.match(_EVM_ADDRESS_RE, v):
                raise ValueError("Invalid EVM wallet address format")
        return v


class AgentWalletResponse(BaseModel):
    wallet_address: str
    chain: str
    wallet_provider: str | None
    is_active: bool
    created_at: UtcDatetime


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Lowercase snake_case: starts with letter, then letters/digits/underscores",
    )
    display_name: str | None = Field(default=None, max_length=100)


class CategoryUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class CategoryAliasCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=100)

    @field_validator("alias")
    @classmethod
    def clean_alias(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("alias must not be blank")
        if "<" in v or ">" in v:
            raise ValueError("alias must not contain HTML characters")
        return v


class CategoryAliasResponse(BaseModel):
    id: str
    alias: str
    is_auto_generated: bool
    created_at: UtcDatetime


class CategoryResponse(BaseModel):
    id: str
    name: str
    display_name: str | None
    is_active: bool
    aliases: list[CategoryAliasResponse]
    created_at: UtcDatetime


class ResolveOrphanRequest(BaseModel):
    raw_category: str = Field(min_length=1, max_length=100)
    category_id: str
    create_alias: bool = True
