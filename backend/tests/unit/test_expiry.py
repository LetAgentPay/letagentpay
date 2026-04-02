"""Tests for request expiry service."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.models import PurchaseRequest, VerificationToken
from app.services.expiry import _cleanup_expired_tokens, _expire_batch
from app.utils import utcnow


def _make_mock_redis():
    """Create a mock Redis for expiry tests."""
    store: dict[str, str] = {}
    redis = AsyncMock()

    async def _get(key):
        return store.get(key)

    async def _incrbyfloat(key, amount):
        current = float(store.get(key, "0"))
        new_val = current + float(amount)
        store[key] = str(new_val)
        return new_val

    async def _expire(key, ttl):
        pass

    async def _publish(channel, message):
        pass

    redis.get = AsyncMock(side_effect=_get)
    redis.incrbyfloat = AsyncMock(side_effect=_incrbyfloat)
    redis.expire = AsyncMock(side_effect=_expire)
    redis.publish = AsyncMock(side_effect=_publish)
    return redis


class TestExpireBatch:
    async def test_expires_old_pending(self, db, agent):
        # Set hold matching the request amount
        agent.held = Decimal("100")
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("100"),
            category="groceries",
            status="pending",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() - timedelta(minutes=5),
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)

        mock_redis = _make_mock_redis()
        with patch("app.services.expiry.get_redis", return_value=mock_redis):
            count = await _expire_batch()
        assert count == 1

        await db.refresh(req)
        assert req.status == "expired"

        # Verify hold was released
        await db.refresh(agent)
        assert agent.held == Decimal("0")

    async def test_skips_not_expired(self, db, agent):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("100"),
            category="groceries",
            status="pending",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() + timedelta(minutes=25),
        )
        db.add(req)
        await db.commit()

        mock_redis = _make_mock_redis()
        with patch("app.services.expiry.get_redis", return_value=mock_redis):
            count = await _expire_batch()
        assert count == 0

        await db.refresh(req)
        assert req.status == "pending"

    async def test_skips_non_pending(self, db, agent):
        req = PurchaseRequest(
            agent_id=agent.id,
            amount=Decimal("100"),
            category="groceries",
            status="approved",
            policy_check={"passed": True, "checks": []},
            expires_at=utcnow() - timedelta(minutes=5),
        )
        db.add(req)
        await db.commit()

        mock_redis = _make_mock_redis()
        with patch("app.services.expiry.get_redis", return_value=mock_redis):
            count = await _expire_batch()
        assert count == 0

    async def test_multiple_expired(self, db, agent):
        agent.held = Decimal("150")
        for _ in range(3):
            req = PurchaseRequest(
                agent_id=agent.id,
                amount=Decimal("50"),
                category="groceries",
                status="pending",
                policy_check={"passed": True, "checks": []},
                expires_at=utcnow() - timedelta(minutes=1),
            )
            db.add(req)
        await db.commit()

        mock_redis = _make_mock_redis()
        with patch("app.services.expiry.get_redis", return_value=mock_redis):
            count = await _expire_batch()
        assert count == 3

        # Verify hold was released
        await db.refresh(agent)
        assert agent.held == Decimal("0")


class TestCleanupExpiredTokens:
    """Tests for _cleanup_expired_tokens — lines 103-112."""

    async def test_removes_expired_tokens(self, db):
        token = VerificationToken(
            email="test@example.com",
            token="expired-token-123",
            expires_at=utcnow() - timedelta(minutes=10),
        )
        db.add(token)
        await db.commit()

        count = await _cleanup_expired_tokens()
        assert count == 1

    async def test_keeps_valid_tokens(self, db):
        token = VerificationToken(
            email="test@example.com",
            token="valid-token-456",
            expires_at=utcnow() + timedelta(hours=1),
        )
        db.add(token)
        await db.commit()

        count = await _cleanup_expired_tokens()
        assert count == 0
