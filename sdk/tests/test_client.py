"""Tests for LetAgentPay client."""

import httpx
import pytest

from letagentpay import LetAgentPay, LetAgentPayError


def make_transport(responses: dict[str, tuple[int, dict]]):
    """Create a mock transport that returns predefined responses by path."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.raw_path.decode()
        # Strip query string for matching
        path_no_query = path.split("?")[0]
        for pattern, (status, body) in responses.items():
            if path_no_query.endswith(pattern):
                return httpx.Response(status, json=body)
        return httpx.Response(404, json={"detail": "Not found"})

    return httpx.MockTransport(handler)


@pytest.fixture
def client():
    transport = make_transport(
        {
            "/requests": (
                201,
                {
                    "request_id": "req-1",
                    "status": "auto_approved",
                    "auto_approved": True,
                    "budget_remaining": "85.0",
                    "policy_check": {
                        "passed": True,
                        "checks": [
                            {
                                "rule": "budget",
                                "result": "pass",
                                "detail": "OK",
                            }
                        ],
                    },
                },
            ),
            "/budget": (
                200,
                {
                    "budget": "100.0",
                    "spent": "15.0",
                    "held": "0.0",
                    "remaining": "85.0",
                    "currency": "USD",
                },
            ),
            "/categories": (
                200,
                {"categories": ["api_calls", "groceries", "saas"]},
            ),
        }
    )
    c = LetAgentPay(token="agt_test123")
    c._client = httpx.Client(
        base_url=c._base_url,
        headers={"Authorization": "Bearer agt_test123"},
        transport=transport,
    )
    return c


class TestClientInit:
    def test_init_with_token(self):
        c = LetAgentPay(token="agt_test")
        assert c._token == "agt_test"
        c.close()

    def test_init_from_env(self, monkeypatch):
        monkeypatch.setenv("LETAGENTPAY_TOKEN", "agt_env")
        c = LetAgentPay()
        assert c._token == "agt_env"
        c.close()

    def test_init_env_base_url(self, monkeypatch):
        monkeypatch.setenv("LETAGENTPAY_TOKEN", "agt_test")
        monkeypatch.setenv("LETAGENTPAY_BASE_URL", "https://custom.api/v1/agent-api")
        c = LetAgentPay()
        assert c._base_url == "https://custom.api/v1/agent-api"
        c.close()

    def test_init_no_token_raises(self, monkeypatch):
        monkeypatch.delenv("LETAGENTPAY_TOKEN", raising=False)
        with pytest.raises(ValueError, match="Token is required"):
            LetAgentPay()

    def test_context_manager(self):
        with LetAgentPay(token="agt_test") as c:
            assert c._token == "agt_test"


class TestRequestPurchase:
    def test_request_purchase(self, client):
        result = client.request_purchase(amount=15.0, category="api_calls")
        assert result.request_id == "req-1"
        assert result.status == "auto_approved"
        assert result.auto_approved is True
        assert result.budget_remaining == 85.0

    def test_request_purchase_with_all_params(self, client):
        result = client.request_purchase(
            amount=15.0,
            category="api_calls",
            merchant_name="OpenAI",
            description="GPT-4 call",
            agent_comment="Document analysis",
        )
        assert result.status == "auto_approved"


class TestCheckBudget:
    def test_check_budget(self, client):
        budget = client.check_budget()
        assert budget.budget == 100.0
        assert budget.spent == 15.0
        assert budget.remaining == 85.0
        assert budget.currency == "USD"


class TestListCategories:
    def test_list_categories(self, client):
        cats = client.list_categories()
        assert cats == ["api_calls", "groceries", "saas"]


class TestCheckRequest:
    def test_check_request(self):
        transport = make_transport(
            {
                "/requests/req-1": (
                    200,
                    {
                        "request_id": "req-1",
                        "status": "pending",
                        "amount": "25.0",
                        "category": "groceries",
                        "created_at": "2026-03-29T10:00:00Z",
                    },
                )
            }
        )
        c = LetAgentPay(token="agt_test")
        c._client = httpx.Client(
            base_url=c._base_url,
            headers={"Authorization": "Bearer agt_test"},
            transport=transport,
        )
        status = c.check_request("req-1")
        assert status.request_id == "req-1"
        assert status.status == "pending"
        assert status.amount == 25.0
        c.close()


class TestConfirmPurchase:
    def test_confirm_purchase(self):
        transport = make_transport(
            {
                "/requests/req-1/confirm": (
                    200,
                    {
                        "request_id": "req-1",
                        "status": "completed",
                        "actual_amount": "14.50",
                    },
                )
            }
        )
        c = LetAgentPay(token="agt_test")
        c._client = httpx.Client(
            base_url=c._base_url,
            headers={"Authorization": "Bearer agt_test"},
            transport=transport,
        )
        result = c.confirm_purchase("req-1", success=True, actual_amount=14.50)
        assert result.status == "completed"
        assert result.actual_amount == 14.50
        c.close()


class TestMyRequests:
    def test_my_requests(self):
        transport = make_transport(
            {
                "/requests": (
                    200,
                    {
                        "requests": [
                            {
                                "request_id": "r1",
                                "status": "pending",
                                "amount": "10.0",
                                "currency": "USD",
                                "category": "api_calls",
                                "created_at": "2026-03-29T10:00:00Z",
                            }
                        ],
                        "total": 1,
                        "limit": 20,
                        "offset": 0,
                    },
                )
            }
        )
        c = LetAgentPay(token="agt_test")
        c._client = httpx.Client(
            base_url=c._base_url,
            headers={"Authorization": "Bearer agt_test"},
            transport=transport,
        )
        result = c.my_requests(status="pending", limit=5)
        assert result.total == 1
        assert result.requests[0].request_id == "r1"
        c.close()


class TestErrorHandling:
    def test_api_error(self):
        transport = make_transport(
            {
                "/budget": (403, {"detail": "Invalid token"}),
            }
        )
        c = LetAgentPay(token="agt_bad")
        c._client = httpx.Client(
            base_url=c._base_url,
            headers={"Authorization": "Bearer agt_bad"},
            transport=transport,
        )
        with pytest.raises(LetAgentPayError) as exc_info:
            c.check_budget()
        assert exc_info.value.status == 403
        assert "Invalid token" in exc_info.value.detail
        c.close()
