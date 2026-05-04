"""Tests for response models."""

from letagentpay.models import (
    BudgetInfo,
    ConfirmResult,
    PurchaseResult,
    RequestList,
    RequestStatus,
)


class TestPurchaseResult:
    def test_from_dict_full(self):
        data = {
            "request_id": "abc-123",
            "status": "auto_approved",
            "currency": "USD",
            "category": "api_calls",
            "original_category": "api calls",
            "policy_check": {
                "passed": True,
                "checks": [
                    {"rule": "budget", "result": "pass", "detail": "Within budget"},
                ],
            },
            "auto_approved": True,
            "budget_remaining": "85.50",
            "expires_at": "2026-04-01T00:00:00Z",
        }
        result = PurchaseResult.from_dict(data)
        assert result.request_id == "abc-123"
        assert result.status == "auto_approved"
        assert result.currency == "USD"
        assert result.auto_approved is True
        assert result.budget_remaining == 85.50
        assert result.policy_check is not None
        assert result.policy_check.passed is True
        assert len(result.policy_check.checks) == 1
        assert result.policy_check.checks[0].rule == "budget"

    def test_from_dict_minimal(self):
        data = {"request_id": "abc-123", "status": "rejected"}
        result = PurchaseResult.from_dict(data)
        assert result.request_id == "abc-123"
        assert result.status == "rejected"
        assert result.policy_check is None
        assert result.budget_remaining is None
        assert result.auto_approved is False


class TestRequestStatus:
    def test_from_dict(self):
        data = {
            "request_id": "abc-123",
            "status": "pending",
            "amount": "25.00",
            "category": "groceries",
            "created_at": "2026-03-29T10:00:00Z",
            "reviewed_at": None,
        }
        status = RequestStatus.from_dict(data)
        assert status.request_id == "abc-123"
        assert status.amount == 25.0
        assert status.reviewed_at is None


class TestConfirmResult:
    def test_from_dict_success(self):
        data = {
            "request_id": "abc-123",
            "status": "completed",
            "actual_amount": "14.50",
        }
        result = ConfirmResult.from_dict(data)
        assert result.status == "completed"
        assert result.actual_amount == 14.50

    def test_from_dict_no_amount(self):
        data = {"request_id": "abc-123", "status": "failed"}
        result = ConfirmResult.from_dict(data)
        assert result.actual_amount is None


class TestBudgetInfo:
    def test_from_dict(self):
        data = {
            "budget": "100.00",
            "spent": "45.00",
            "held": "10.00",
            "remaining": "45.00",
            "currency": "USD",
        }
        budget = BudgetInfo.from_dict(data)
        assert budget.budget == 100.0
        assert budget.spent == 45.0
        assert budget.held == 10.0
        assert budget.remaining == 45.0
        assert budget.currency == "USD"


class TestRequestList:
    def test_from_dict(self):
        data = {
            "requests": [
                {
                    "request_id": "r1",
                    "status": "pending",
                    "amount": "10.00",
                    "currency": "USD",
                    "category": "api_calls",
                    "merchant": None,
                    "description": "Test",
                    "created_at": "2026-03-29T10:00:00Z",
                    "reviewed_at": None,
                    "expires_at": None,
                }
            ],
            "total": 1,
            "limit": 20,
            "offset": 0,
        }
        result = RequestList.from_dict(data)
        assert result.total == 1
        assert len(result.requests) == 1
        assert result.requests[0].request_id == "r1"
        assert result.requests[0].amount == 10.0

    def test_from_dict_empty(self):
        data = {"requests": [], "total": 0, "limit": 20, "offset": 0}
        result = RequestList.from_dict(data)
        assert result.requests == []
        assert result.total == 0
