"""Tests for @guard decorator and make_guarded_tool."""

import httpx
import pytest

from letagentpay import LetAgentPay, LetAgentPayError, guard, make_guarded_tool


def _make_client(status: str = "auto_approved"):
    """Create a client with a mocked transport."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "request_id": "req-guard",
                "status": status,
                "auto_approved": status == "auto_approved",
            },
        )

    c = LetAgentPay(token="agt_test")
    c._client = httpx.Client(
        base_url=c._base_url,
        headers={"Authorization": "Bearer agt_test"},
        transport=httpx.MockTransport(handler),
    )
    return c


class TestGuardDecorator:
    def test_approved_executes_function(self):
        client = _make_client("auto_approved")

        @guard(client=client, category="test", amount=5.0)
        def do_work(x: int) -> int:
            return x * 2

        assert do_work(3) == 6

    def test_rejected_raises_error(self):
        client = _make_client("rejected")

        @guard(client=client, category="test", amount=5.0)
        def do_work(x: int) -> int:
            return x * 2

        with pytest.raises(LetAgentPayError) as exc_info:
            do_work(3)
        assert exc_info.value.status == 403
        assert "rejected" in exc_info.value.detail

    def test_pending_raises_error(self):
        client = _make_client("pending")

        @guard(client=client, category="test", amount=5.0)
        def do_work() -> str:
            return "done"

        with pytest.raises(LetAgentPayError) as exc_info:
            do_work()
        assert "pending" in exc_info.value.detail

    def test_amount_from_args(self):
        client = _make_client("auto_approved")

        @guard(client=client, category="test")
        def buy(amount: float, item: str) -> str:
            return f"bought {item}"

        assert buy(10.0, "widget") == "bought widget"

    def test_amount_from_kwargs(self):
        client = _make_client("auto_approved")

        @guard(client=client, category="test")
        def buy(item: str, amount: float = 0) -> str:
            return f"bought {item}"

        assert buy("widget", amount=10.0) == "bought widget"

    def test_no_amount_raises(self):
        client = _make_client("auto_approved")

        @guard(client=client, category="test")
        def do_work() -> str:
            return "done"

        with pytest.raises(ValueError, match="could not determine amount"):
            do_work()

    def test_fixed_amount_overrides_args(self):
        """When amount is set on the decorator, function args are ignored for policy check."""
        client = _make_client("auto_approved")

        @guard(client=client, category="test", amount=0.03)
        def call_api(prompt: str) -> str:
            return f"response to {prompt}"

        assert call_api("hello") == "response to hello"

    def test_preserves_function_metadata(self):
        client = _make_client("auto_approved")

        @guard(client=client, category="test", amount=1.0)
        def my_func():
            """My docstring."""
            pass

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My docstring."


class TestMakeGuardedTool:
    def test_guarded_tool_approved(self):
        client = _make_client("auto_approved")

        def buy_item(item: str) -> str:
            return f"bought {item}"

        guarded = make_guarded_tool(
            buy_item, client=client, category="test", amount=9.99
        )
        assert guarded("widget") == "bought widget"

    def test_guarded_tool_rejected(self):
        client = _make_client("rejected")

        def buy_item(item: str) -> str:
            return f"bought {item}"

        guarded = make_guarded_tool(
            buy_item, client=client, category="test", amount=9.99
        )
        with pytest.raises(LetAgentPayError):
            guarded("widget")
