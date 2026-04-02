"""Tests for shared approve/reject logic in request_actions service."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models import Account, Agent
from app.services.request_actions import (
    approve_purchase_request,
    reject_purchase_request,
)


class TestApprovePurchaseRequest:
    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_sets_status_approved(
        self,
        _mock_replenish,
        _mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        await db.refresh(pending_request)
        assert pending_request.status == "approved"
        assert pending_request.reviewed_at is not None

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_converts_hold_to_spent_in_db(
        self,
        _mock_replenish,
        _mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        original_spent = agent.spent
        original_held = agent.held

        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.spent == original_spent + pending_request.amount
        assert refreshed_agent.held == max(
            original_held - pending_request.amount, Decimal("0.00")
        )

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_updates_account_spent(
        self,
        _mock_replenish,
        _mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        original_account_spent = account.account_spent
        original_account_held = account.account_held

        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        result = await db.execute(select(Account).where(Account.id == account.id))
        refreshed_account = result.scalar_one()
        assert (
            refreshed_account.account_spent
            == original_account_spent + pending_request.amount
        )
        assert refreshed_account.account_held == max(
            original_account_held - pending_request.amount, Decimal("0.00")
        )

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_adds_spent_to_redis(
        self,
        _mock_replenish,
        _mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        # add_spent and add_account_spent each call incrby 3 times (daily, weekly, monthly)
        incrby_calls = mock_redis.incrby.call_args_list
        # At least 6 incrby calls: 3 for agent spent + 3 for account spent
        assert len(incrby_calls) >= 6
        # Verify the amount in subunits (1500.00 * 100 = 150000)
        expected_cents = 150000
        spent_amounts = [call.args[1] for call in incrby_calls]
        assert spent_amounts.count(expected_cents) >= 6

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_removes_held_from_redis(
        self,
        _mock_replenish,
        _mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        # remove_held and remove_account_held each call decrby 3 times (daily, weekly, monthly)
        decrby_calls = mock_redis.decrby.call_args_list
        assert len(decrby_calls) >= 6
        expected_cents = 150000
        held_amounts = [call.args[1] for call in decrby_calls]
        assert held_amounts.count(expected_cents) >= 6

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_publishes_request_updated_event(
        self,
        _mock_replenish,
        mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        call_args_list = mock_publish.call_args_list
        request_updated_calls = [
            c for c in call_args_list if c.args[2] == "request_updated"
        ]
        assert len(request_updated_calls) == 1
        payload = request_updated_calls[0].args[3]
        assert payload["request_id"] == pending_request.id
        assert payload["status"] == "approved"

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    @patch("app.services.request_actions.maybe_auto_replenish", new_callable=AsyncMock)
    async def test_publishes_budget_updated_event(
        self,
        _mock_replenish,
        mock_publish,
        db,
        mock_redis,
        agent,
        account,
        pending_request,
    ):
        await approve_purchase_request(db, mock_redis, pending_request, account.id)

        call_args_list = mock_publish.call_args_list
        budget_updated_calls = [
            c for c in call_args_list if c.args[2] == "budget_updated"
        ]
        assert len(budget_updated_calls) == 1
        payload = budget_updated_calls[0].args[3]
        assert "budget" in payload
        assert "spent" in payload


class TestRejectPurchaseRequest:
    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    async def test_sets_status_rejected(
        self, _mock_publish, db, mock_redis, agent, account, pending_request
    ):
        await reject_purchase_request(db, mock_redis, pending_request, account.id)

        await db.refresh(pending_request)
        assert pending_request.status == "rejected"
        assert pending_request.reviewed_at is not None

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    async def test_releases_hold_from_agent(
        self, _mock_publish, db, mock_redis, agent, account, pending_request
    ):
        original_held = agent.held

        await reject_purchase_request(db, mock_redis, pending_request, account.id)

        result = await db.execute(select(Agent).where(Agent.id == agent.id))
        refreshed_agent = result.scalar_one()
        assert refreshed_agent.held == max(
            original_held - pending_request.amount, Decimal("0.00")
        )

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    async def test_releases_hold_from_account(
        self, _mock_publish, db, mock_redis, agent, account, pending_request
    ):
        original_account_held = account.account_held

        await reject_purchase_request(db, mock_redis, pending_request, account.id)

        result = await db.execute(select(Account).where(Account.id == account.id))
        refreshed_account = result.scalar_one()
        assert refreshed_account.account_held == max(
            original_account_held - pending_request.amount, Decimal("0.00")
        )

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    async def test_removes_held_from_redis(
        self, _mock_publish, db, mock_redis, agent, account, pending_request
    ):
        await reject_purchase_request(db, mock_redis, pending_request, account.id)

        # remove_held + remove_account_held = 6 decrby calls
        decrby_calls = mock_redis.decrby.call_args_list
        assert len(decrby_calls) >= 6
        expected_cents = 150000
        held_amounts = [call.args[1] for call in decrby_calls]
        assert held_amounts.count(expected_cents) >= 6

    @patch("app.services.request_actions.publish_event", new_callable=AsyncMock)
    async def test_publishes_request_updated_event(
        self, mock_publish, db, mock_redis, agent, account, pending_request
    ):
        await reject_purchase_request(db, mock_redis, pending_request, account.id)

        assert mock_publish.call_count == 1
        call = mock_publish.call_args
        assert call.args[2] == "request_updated"
        payload = call.args[3]
        assert payload["request_id"] == pending_request.id
        assert payload["status"] == "rejected"
