"""Guard decorator and tool wrapper for LetAgentPay."""

from __future__ import annotations

import functools
from typing import Callable

from letagentpay.client import LetAgentPay, LetAgentPayError


def guard(
    token: str | None = None,
    client: LetAgentPay | None = None,
    category: str = "other",
    amount: float | None = None,
    description: str | None = None,
    agent_comment: str | None = None,
):
    """Decorator that checks the spending policy before executing a function.

    The decorated function must accept ``amount`` as first positional argument
    or keyword argument, unless a fixed ``amount`` is provided to the decorator.

    Usage::

        @guard(token="agt_...", category="api_calls", amount=0.03)
        def call_openai(prompt: str) -> str:
            return openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            ).choices[0].message.content

    Args:
        token: Agent bearer token. Either token or client must be provided.
        client: Existing LetAgentPay client instance.
        category: Purchase category for the request.
        amount: Fixed amount per call. If not set, extracted from function args.
        description: Purchase description.
        agent_comment: Optional comment explaining the purchase.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            resolved_amount = amount
            if resolved_amount is None:
                resolved_amount = kwargs.get("amount") or (args[0] if args else None)
            if resolved_amount is None:
                raise ValueError(
                    "guard: could not determine amount from arguments. "
                    "Pass amount= to @guard() or as the first function argument."
                )

            _client = client or LetAgentPay(token=token)
            try:
                result = _client.request_purchase(
                    amount=resolved_amount,
                    category=category,
                    description=description or f"Auto-guarded call to {func.__name__}",
                    agent_comment=agent_comment,
                )
                if result.status in ("auto_approved", "approved"):
                    return func(*args, **kwargs)
                else:
                    raise LetAgentPayError(
                        403,
                        f"Purchase request {result.status}: {result.request_id}",
                    )
            finally:
                if not client:
                    _client.close()

        return wrapper

    return decorator


def make_guarded_tool(
    func: Callable,
    token: str | None = None,
    client: LetAgentPay | None = None,
    category: str = "other",
    amount: float | None = None,
    description: str | None = None,
    agent_comment: str | None = None,
) -> Callable:
    """Wrap a function as a guarded tool for AI tool use.

    Usage::

        def buy_item(amount: float, item: str) -> str:
            return f"Bought {item} for ${amount}"

        guarded_buy = make_guarded_tool(
            buy_item, token="agt_...", category="groceries", amount=9.99
        )
    """
    return guard(
        token=token,
        client=client,
        category=category,
        amount=amount,
        description=description,
        agent_comment=agent_comment,
    )(func)
