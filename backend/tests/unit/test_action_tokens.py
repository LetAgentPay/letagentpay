"""Tests for action tokens service."""

import json
from unittest.mock import patch

from app.services.action_tokens import (
    _PREFIX,
    create_action_tokens,
    execute_action_token,
)


class TestCreateActionTokens:
    async def test_creates_two_tokens(self, mock_redis):
        mock_redis.pipeline = lambda: _MockPipeline(mock_redis)

        tokens = await create_action_tokens(
            mock_redis, "acc-1", "req-1", ttl_seconds=1800
        )

        assert tokens.approve.startswith("act_")
        assert tokens.reject.startswith("act_")
        assert tokens.approve != tokens.reject
        # Check tokens are in Redis store
        assert f"action_token:{tokens.approve}" in mock_redis._store
        assert f"action_token:{tokens.reject}" in mock_redis._store

    async def test_token_data_contains_correct_fields(self, mock_redis):
        mock_redis.pipeline = lambda: _MockPipeline(mock_redis)

        tokens = await create_action_tokens(
            mock_redis, "acc-1", "req-1", ttl_seconds=1800
        )

        approve_data = json.loads(mock_redis._store[f"action_token:{tokens.approve}"])
        assert approve_data["account_id"] == "acc-1"
        assert approve_data["request_id"] == "req-1"
        assert approve_data["action"] == "approve"

        reject_data = json.loads(mock_redis._store[f"action_token:{tokens.reject}"])
        assert reject_data["action"] == "reject"

    async def test_tokens_store_paired_keys(self, mock_redis):
        mock_redis.pipeline = lambda: _MockPipeline(mock_redis)

        tokens = await create_action_tokens(
            mock_redis, "acc-1", "req-1", ttl_seconds=1800
        )

        approve_data = json.loads(mock_redis._store[f"action_token:{tokens.approve}"])
        reject_data = json.loads(mock_redis._store[f"action_token:{tokens.reject}"])

        assert approve_data["paired_key"] == f"{_PREFIX}{tokens.reject}"
        assert reject_data["paired_key"] == f"{_PREFIX}{tokens.approve}"


class TestExecuteActionToken:
    @patch("app.services.action_tokens.get_redis")
    async def test_invalid_token_returns_failure(self, mock_get_redis, db, mock_redis):
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_invalid")

        assert not result.success
        assert result.status == "invalid"

    @patch("app.services.action_tokens.get_redis")
    async def test_corrupt_json_returns_failure(self, mock_get_redis, db, mock_redis):
        # Put corrupt data directly in store so eval finds it
        mock_redis._store[f"{_PREFIX}act_corrupt"] = "not valid json{{{"
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_corrupt")

        assert not result.success
        assert result.status == "invalid"

    @patch("app.services.action_tokens.get_redis")
    async def test_missing_fields_returns_failure(self, mock_get_redis, db, mock_redis):
        mock_redis._store[f"{_PREFIX}act_incomplete"] = json.dumps({"account_id": "x"})
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_incomplete")

        assert not result.success
        assert result.status == "invalid"

    @patch("app.services.action_tokens.get_redis")
    async def test_approve_pending_request(
        self, mock_get_redis, db, mock_redis, pending_request, agent, account
    ):
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired_reject",
            }
        )
        mock_redis._store[f"{_PREFIX}act_test_approve"] = token_data
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_test_approve")

        assert result.success
        assert result.action == "approve"
        assert result.status == "approved"

        await db.refresh(pending_request)
        assert pending_request.status == "approved"

    @patch("app.services.action_tokens.get_redis")
    async def test_reject_pending_request(
        self, mock_get_redis, db, mock_redis, pending_request, agent, account
    ):
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "reject",
                "paired_key": f"{_PREFIX}act_paired_approve",
            }
        )
        mock_redis._store[f"{_PREFIX}act_test_reject"] = token_data
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_test_reject")

        assert result.success
        assert result.action == "reject"
        assert result.status == "rejected"

        await db.refresh(pending_request)
        assert pending_request.status == "rejected"

    @patch("app.services.action_tokens.get_redis")
    async def test_already_processed_request(
        self, mock_get_redis, db, mock_redis, pending_request, agent, account
    ):
        # First, mark as approved directly
        pending_request.status = "approved"
        await db.commit()

        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_test"] = token_data
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_test")

        assert not result.success
        assert result.status == "approved"
        assert "already been approved" in result.message

    @patch("app.services.action_tokens.get_redis")
    async def test_approve_deletes_paired_reject_token(
        self, mock_get_redis, db, mock_redis, pending_request, agent, account
    ):
        """When approve token is used, the paired reject token is deleted from Redis."""
        paired_reject_key = f"{_PREFIX}act_reject_token_123"
        mock_redis._store[paired_reject_key] = "should_be_deleted"

        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": paired_reject_key,
            }
        )
        mock_redis._store[f"{_PREFIX}act_approve_123"] = token_data
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_approve_123")

        assert result.success
        assert paired_reject_key not in mock_redis._store

    @patch("app.services.action_tokens.get_redis")
    async def test_reject_deletes_paired_approve_token(
        self, mock_get_redis, db, mock_redis, pending_request, agent, account
    ):
        """When reject token is used, the paired approve token is deleted from Redis."""
        paired_approve_key = f"{_PREFIX}act_approve_token_456"
        mock_redis._store[paired_approve_key] = "should_be_deleted"

        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "reject",
                "paired_key": paired_approve_key,
            }
        )
        mock_redis._store[f"{_PREFIX}act_reject_456"] = token_data
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_reject_456")

        assert result.success
        assert paired_approve_key not in mock_redis._store

    @patch("app.services.action_tokens.get_redis")
    async def test_second_token_fails_after_first_consumed(
        self, mock_get_redis, db, mock_redis, pending_request, agent, account
    ):
        """Simulates race condition: after one token is consumed, the paired
        token is deleted atomically by Lua script, so a second attempt returns 'invalid'.
        """
        approve_key = f"{_PREFIX}act_approve_race"
        reject_key = f"{_PREFIX}act_reject_race"

        approve_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "approve",
                "paired_key": reject_key,
            }
        )
        reject_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": pending_request.id,
                "action": "reject",
                "paired_key": approve_key,
            }
        )

        # Both tokens exist in Redis initially
        mock_redis._store[approve_key] = approve_data
        mock_redis._store[reject_key] = reject_data
        mock_get_redis.return_value = mock_redis

        # First call: approve succeeds (Lua script atomically deletes paired reject)
        result1 = await execute_action_token(db, "act_approve_race")
        assert result1.success
        assert result1.action == "approve"
        assert result1.status == "approved"

        # Reject token was deleted atomically by the Lua script
        assert reject_key not in mock_redis._store

        # Second call: reject fails because token was invalidated
        result2 = await execute_action_token(db, "act_reject_race")
        assert not result2.success
        assert result2.status == "invalid"

    @patch("app.services.action_tokens.get_redis")
    async def test_expired_request_returns_failure(
        self, mock_get_redis, db, mock_redis, expired_request, agent, account
    ):
        """Valid token but request has already expired in DB."""
        token_data = json.dumps(
            {
                "account_id": account.id,
                "request_id": expired_request.id,
                "action": "approve",
                "paired_key": f"{_PREFIX}act_paired",
            }
        )
        mock_redis._store[f"{_PREFIX}act_expired_test"] = token_data
        mock_get_redis.return_value = mock_redis

        result = await execute_action_token(db, "act_expired_test")

        assert not result.success
        assert result.status == "expired"
        assert "expired" in result.message

    async def test_full_flow_create_and_execute(
        self, db, mock_redis, pending_request, agent, account
    ):
        """End-to-end: create tokens, use one, verify paired is invalidated."""
        mock_redis.pipeline = lambda: _MockPipeline(mock_redis)

        tokens = await create_action_tokens(
            mock_redis, account.id, pending_request.id, ttl_seconds=1800
        )

        # Both tokens exist
        assert f"{_PREFIX}{tokens.approve}" in mock_redis._store
        assert f"{_PREFIX}{tokens.reject}" in mock_redis._store

        with patch("app.services.action_tokens.get_redis", return_value=mock_redis):
            result = await execute_action_token(db, tokens.approve)

        assert result.success
        assert result.status == "approved"

        # Paired reject token was deleted atomically by Lua script
        assert f"{_PREFIX}{tokens.reject}" not in mock_redis._store

        # Trying reject token now fails
        with patch("app.services.action_tokens.get_redis", return_value=mock_redis):
            result2 = await execute_action_token(db, tokens.reject)

        assert not result2.success
        assert result2.status == "invalid"


class _MockPipeline:
    """Minimal Redis pipeline mock for testing."""

    def __init__(self, redis):
        self._redis = redis
        self._ops = []

    def setex(self, key, ttl, value):
        self._ops.append(("setex", key, value))

    async def execute(self):
        for _op, key, value in self._ops:
            self._redis._store[key] = value
