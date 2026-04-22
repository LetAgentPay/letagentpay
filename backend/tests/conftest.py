from datetime import UTC, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, DateTime, TypeDecorator, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import (
    Account,
    Agent,
    Base,
    BudgetRule,
    Category,
    CategoryAlias,
    PurchaseRequest,
)
from app.utils import utcnow

# ---------------------------------------------------------------------------
# Database fixtures — in-memory SQLite (sync engine wrapped in async shim)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite://"


class _TZDateTime(TypeDecorator):
    """SQLite-compatible DateTime that preserves UTC timezone on read."""

    impl = DateTime
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


# Replace JSONB with JSON, DateTime(timezone=True) with TZDateTime for SQLite
from sqlalchemy.dialects.postgresql import JSONB

for table in Base.metadata.tables.values():
    for column in table.columns:
        if isinstance(column.type, JSONB):
            column.type = JSON()
        elif isinstance(column.type, DateTime) and column.type.timezone:
            column.type = _TZDateTime()


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db(db_engine):
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Patch async_session in expiry service to use test DB
    import app.services.expiry as expiry_mod

    original_session = getattr(expiry_mod, "async_session", None)
    expiry_mod.async_session = session_factory

    async with session_factory() as s:
        yield s

    if original_session is not None:
        expiry_mod.async_session = original_session


# ---------------------------------------------------------------------------
# Redis mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_redis():
    """In-memory dict-based Redis mock."""
    store: dict[str, str] = {}

    redis = AsyncMock()

    async def _get(key):
        return store.get(key)

    async def _set(key, value, *args, **kwargs):
        store[key] = str(value)

    async def _delete(*keys):
        for k in keys:
            store.pop(k, None)

    async def _incr(key):
        current = int(store.get(key, "0"))
        new_val = current + 1
        store[key] = str(new_val)
        return new_val

    async def _incrby(key, amount):
        current = int(store.get(key, "0"))
        new_val = current + int(amount)
        store[key] = str(new_val)
        return new_val

    async def _decrby(key, amount):
        current = int(store.get(key, "0"))
        new_val = current - int(amount)
        store[key] = str(new_val)
        return new_val

    async def _incrbyfloat(key, amount):
        current = float(store.get(key, "0"))
        new_val = current + float(amount)
        store[key] = str(new_val)
        return new_val

    async def _expire(key, ttl):
        pass  # No-op for tests

    async def _ttl(key):
        return 900 if key in store else -2

    async def _exists(*keys):
        return sum(1 for k in keys if k in store)

    async def _publish(channel, message):
        pass  # No-op for tests

    async def _eval(script, numkeys, *keys_and_args):
        """Simulate Lua eval for action token, rate limit, and MGET scripts."""
        import json as _json

        if numkeys >= 1:
            key = keys_and_args[0]

            # Multi-GET script: reads N keys atomically
            if "for i = 1, #KEYS" in script and "GET" in script:
                keys = keys_and_args[:numkeys]
                return [store.get(k, "0") for k in keys]

            # DECRBY-floor script: decrement clamped to 0
            if "DECRBY" in script and "INCRBY" in script:
                amount = int(keys_and_args[numkeys])  # ARGV[1]
                current = int(store.get(key, "0"))
                new_val = current - amount
                if new_val < 0:
                    new_val = 0
                store[key] = str(new_val)
                return new_val

            # Rate limit script: INCR + EXPIRE atomically
            if "INCR" in script and "EXPIRE" in script:
                current = int(store.get(key, "0"))
                new_val = current + 1
                store[key] = str(new_val)
                return new_val

            # Action token consume script: GET-and-DELETE + delete paired
            data = store.pop(key, None)
            if data is None:
                return None
            try:
                parsed = _json.loads(data)
                paired_key = parsed.get("paired_key")
                if paired_key:
                    store.pop(paired_key, None)
            except (ValueError, AttributeError):
                pass
            return data
        return None

    async def _setex(key, ttl, value):
        store[key] = str(value)

    async def _scan_iter(match=None, count=100):
        """Simulate scan_iter for key pattern matching."""
        import fnmatch

        pattern = match or "*"
        for key in list(store.keys()):
            if fnmatch.fnmatch(key, pattern):
                yield key

    class _MockPipeline:
        """Minimal Redis pipeline mock."""

        def __init__(self):
            self._ops: list[tuple] = []

        def set(self, key, value):
            self._ops.append(("set", key, str(value)))

        def setex(self, key, ttl, value):
            self._ops.append(("set", key, str(value)))

        def expire(self, key, ttl):
            pass  # No-op for tests

        async def execute(self):
            for _op, key, value in self._ops:
                store[key] = value

    def _pipeline():
        return _MockPipeline()

    redis.get = AsyncMock(side_effect=_get)
    redis.setex = AsyncMock(side_effect=_setex)
    redis.set = AsyncMock(side_effect=_set)
    redis.delete = AsyncMock(side_effect=_delete)
    redis.incr = AsyncMock(side_effect=_incr)
    redis.incrby = AsyncMock(side_effect=_incrby)
    redis.decrby = AsyncMock(side_effect=_decrby)
    redis.incrbyfloat = AsyncMock(side_effect=_incrbyfloat)
    redis.expire = AsyncMock(side_effect=_expire)
    redis.ttl = AsyncMock(side_effect=_ttl)
    redis.exists = AsyncMock(side_effect=_exists)
    redis.publish = AsyncMock(side_effect=_publish)
    redis.eval = AsyncMock(side_effect=_eval)
    redis.scan_iter = _scan_iter  # async generator, not AsyncMock
    redis.pipeline = _pipeline
    redis._store = store  # expose for assertions

    return redis


# ---------------------------------------------------------------------------
# App client
# ---------------------------------------------------------------------------


@pytest.fixture
async def client(db, mock_redis):
    """Async test client with overridden DB and Redis."""

    async def _override_db():
        yield db

    def _override_redis():
        return mock_redis

    app.dependency_overrides[get_db] = _override_db

    # Monkey-patch get_redis at module level for services that call it directly
    import app.redis as redis_mod

    original = redis_mod.get_redis
    redis_mod.get_redis = _override_redis

    # Also patch in routers that import get_redis
    import app.routers.agent_api as agent_api_mod
    import app.routers.auth as auth_mod
    import app.routers.budget_rules as budget_rules_mod
    import app.routers.events as events_mod
    import app.routers.me as me_mod
    import app.routers.notifications as notifications_mod
    import app.routers.policy as policy_mod
    import app.routers.requests as requests_mod
    import app.routers.x402 as x402_mod

    policy_mod.get_redis = _override_redis
    requests_mod.get_redis = _override_redis
    agent_api_mod.get_redis = _override_redis
    events_mod.get_redis = _override_redis
    budget_rules_mod.get_redis = _override_redis
    auth_mod.get_redis = _override_redis
    me_mod.get_redis = _override_redis
    x402_mod.get_redis = _override_redis

    # Patch get_redis in playground service
    import app.services.playground as playground_mod

    original_playground_redis = playground_mod.get_redis
    playground_mod.get_redis = _override_redis

    # Patch get_redis in notification-related modules
    import app.services.action_tokens as action_tokens_mod

    original_action_tokens_redis = action_tokens_mod.get_redis
    action_tokens_mod.get_redis = _override_redis
    notifications_mod.get_redis = _override_redis

    # Mock notification dispatcher to avoid real push/email/telegram calls
    import app.services.notification_dispatcher as dispatcher_mod

    original_dispatch = dispatcher_mod.dispatch_notification

    async def _mock_dispatch(*args, **kwargs):
        pass

    dispatcher_mod.dispatch_notification = _mock_dispatch

    # Also patch the import in agent_api
    import app.routers.agent_api as agent_api_dispatch

    original_agent_api_dispatch = agent_api_dispatch.dispatch_notification
    agent_api_dispatch.dispatch_notification = _mock_dispatch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    redis_mod.get_redis = original
    policy_mod.get_redis = original
    requests_mod.get_redis = original
    agent_api_mod.get_redis = original
    events_mod.get_redis = original
    budget_rules_mod.get_redis = original
    auth_mod.get_redis = original
    me_mod.get_redis = original
    x402_mod.get_redis = original
    dispatcher_mod.dispatch_notification = original_dispatch
    agent_api_dispatch.dispatch_notification = original_agent_api_dispatch
    notifications_mod.get_redis = original
    action_tokens_mod.get_redis = original_action_tokens_redis
    playground_mod.get_redis = original_playground_redis


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def make_jwt(account_id: str, email: str = "test@example.com") -> str:
    payload = {
        "sub": account_id,
        "email": email,
        "exp": utcnow() + timedelta(days=7),
        "iat": utcnow(),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# Data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def account(db: AsyncSession) -> Account:
    acc = Account(email="test@example.com")
    db.add(acc)
    await db.commit()
    await db.refresh(acc)

    # Create default categories for the test account
    default_cats = [
        "accommodation",
        "api",
        "clothing",
        "education",
        "electronics",
        "entertainment",
        "flights",
        "food_delivery",
        "gas",
        "groceries",
        "health",
        "household",
        "other",
        "restaurants",
        "subscriptions",
        "taxi",
        "transport",
    ]
    cat_objects = {}
    for name in default_cats:
        cat = Category(
            account_id=acc.id,
            name=name,
            display_name=name.replace("_", " ").title(),
        )
        db.add(cat)
        cat_objects[name] = cat

    await db.flush()

    # Create default aliases
    default_aliases = {
        "food": "food_delivery",
        "delivery": "food_delivery",
        "uber_eats": "food_delivery",
        "software": "subscriptions",
        "hotel": "accommodation",
        "uber": "taxi",
        "grocery": "groceries",
        "dining": "restaurants",
    }
    for alias_name, target in default_aliases.items():
        alias = CategoryAlias(
            account_id=acc.id,
            category_id=cat_objects[target].id,
            alias=alias_name,
        )
        db.add(alias)

    await db.commit()
    return acc


@pytest.fixture
async def agent(db: AsyncSession, account: Account) -> Agent:
    ag = Agent(
        account_id=account.id,
        name="Test Agent",
        description="A test agent",
        budget=Decimal("10000.00"),
        policy={
            "daily_limit": 5000,
            "per_request_limit": 2000,
            "allowed_categories": ["groceries", "food_delivery"],
            "auto_approve": {
                "enabled": True,
                "max_amount": 500,
                "categories": ["groceries"],
            },
        },
        policy_text="Groceries and food delivery, up to 5000/day, auto-approve under 500",
    )
    db.add(ag)
    await db.commit()
    await db.refresh(ag)
    return ag


@pytest.fixture
def auth_cookies(account: Account) -> dict[str, str]:
    token = make_jwt(account.id, account.email)
    return {"access_token": token}


@pytest.fixture
async def auth_client(client, account):
    """Async test client with auth cookies pre-set (avoids httpx per-request cookies deprecation)."""
    token = make_jwt(account.id, account.email)
    client.cookies.set("access_token", token)
    yield client
    client.cookies.clear()


@pytest.fixture
async def pending_request(db: AsyncSession, agent: Agent) -> PurchaseRequest:
    req = PurchaseRequest(
        agent_id=agent.id,
        amount=Decimal("1500.00"),
        category="groceries",
        merchant="Test Store",
        description="Weekly groceries",
        status="pending",
        policy_check={"passed": True, "checks": []},
        expires_at=utcnow() + timedelta(minutes=30),
    )
    db.add(req)
    # Set corresponding hold on agent and account
    agent.held = agent.held + Decimal("1500.00")
    account_result = await db.execute(
        select(Account).where(Account.id == agent.account_id)
    )
    acct = account_result.scalar_one()
    acct.account_held = acct.account_held + Decimal("1500.00")
    await db.commit()
    await db.refresh(req)
    await db.refresh(agent)
    return req


@pytest.fixture
async def expired_request(db: AsyncSession, agent: Agent) -> PurchaseRequest:
    req = PurchaseRequest(
        agent_id=agent.id,
        amount=Decimal("100.00"),
        category="groceries",
        merchant="Old Store",
        status="pending",
        policy_check={"passed": True, "checks": []},
        expires_at=utcnow() - timedelta(minutes=5),
    )
    db.add(req)
    # Set corresponding hold on agent and account
    agent.held = agent.held + Decimal("100.00")
    account_result = await db.execute(
        select(Account).where(Account.id == agent.account_id)
    )
    acct = account_result.scalar_one()
    acct.account_held = acct.account_held + Decimal("100.00")
    await db.commit()
    await db.refresh(req)
    await db.refresh(agent)
    return req


@pytest.fixture
async def budget_rule_daily(db: AsyncSession, account: Account) -> BudgetRule:
    rule = BudgetRule(
        account_id=account.id,
        name="Daily limit",
        limit_type="daily",
        limit_amount=Decimal("200.00"),
        priority=0,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@pytest.fixture
async def budget_rule_monthly(db: AsyncSession, account: Account) -> BudgetRule:
    rule = BudgetRule(
        account_id=account.id,
        name="Monthly limit",
        limit_type="monthly",
        limit_amount=Decimal("3000.00"),
        priority=0,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule
