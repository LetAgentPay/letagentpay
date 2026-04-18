#!/usr/bin/env python3
"""LangChain integration example — LetAgentPay as a LangChain tool.

This example shows how to wrap LetAgentPay as a LangChain tool so that
any LangChain agent can request purchases through the policy engine.

Requirements:
    pip install letagentpay langchain langchain-openai

Usage:
    export LETAGENTPAY_TOKEN=agt_<your_token>
    export OPENAI_API_KEY=sk-...
    python examples/langchain_tool.py
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from letagentpay import LetAgentPay, LetAgentPayError


# --- Tool Definition ---


class PurchaseRequestInput(BaseModel):
    """Input schema for the purchase request tool."""

    amount: float = Field(description="Amount to spend in dollars")
    category: str = Field(
        description=(
            "Spending category (e.g. groceries, electronics, subscriptions). "
            "Unknown categories are auto-mapped to the closest match."
        )
    )
    merchant_name: str = Field(description="Name of the merchant or service")
    description: str = Field(description="What the purchase is for")


class LetAgentPayTool(BaseTool):
    """LangChain tool that requests purchase approval through LetAgentPay.

    The tool sends a purchase request to the LetAgentPay policy engine,
    which checks budgets, category restrictions, spending limits, and
    schedules before approving or rejecting the purchase.
    """

    name: str = "request_purchase"
    description: str = (
        "Request approval to spend money on a purchase. "
        "Use this BEFORE making any purchase. The request will be checked "
        "against spending policies and either auto-approved, sent for review, "
        "or rejected. Returns the decision and remaining budget."
    )
    args_schema: type[BaseModel] = PurchaseRequestInput

    client: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, token: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.client = LetAgentPay(token=token, base_url=base_url)

    def _run(
        self,
        amount: float,
        category: str,
        merchant_name: str,
        description: str,
    ) -> str:
        try:
            result = self.client.request_purchase(
                amount=amount,
                category=category,
                merchant_name=merchant_name,
                description=description,
            )
            response = {
                "status": result.status,
                "request_id": result.request_id,
                "budget_remaining": result.budget_remaining,
            }
            if result.status == "auto_approved":
                response["message"] = "Purchase approved. You may proceed."
            elif result.status == "pending":
                response["message"] = (
                    "Purchase is pending human review. "
                    "Wait for approval before proceeding."
                )
            else:
                response["message"] = "Purchase rejected by policy."
                if result.policy_check:
                    failed = [
                        c.detail
                        for c in result.policy_check.checks
                        if c.result == "fail"
                    ]
                    response["reasons"] = failed
            return json.dumps(response)
        except LetAgentPayError as e:
            return json.dumps({"error": e.detail, "status_code": e.status})


class CheckBudgetTool(BaseTool):
    """LangChain tool that checks the agent's budget status."""

    name: str = "check_budget"
    description: str = (
        "Check the current budget status including spent, held, and remaining amounts."
    )

    client: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, token: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.client = LetAgentPay(token=token, base_url=base_url)

    def _run(self) -> str:
        try:
            budget = self.client.check_budget()
            return json.dumps({
                "budget": budget.budget,
                "spent": budget.spent,
                "held": budget.held,
                "remaining": budget.remaining,
                "currency": budget.currency,
            })
        except LetAgentPayError as e:
            return json.dumps({"error": e.detail, "status_code": e.status})


class ListCategoriesTool(BaseTool):
    """LangChain tool that lists valid spending categories."""

    name: str = "list_categories"
    description: str = "List valid spending categories for purchase requests."

    client: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, token: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.client = LetAgentPay(token=token, base_url=base_url)

    def _run(self) -> str:
        try:
            categories = self.client.list_categories()
            return json.dumps({"categories": categories})
        except LetAgentPayError as e:
            return json.dumps({"error": e.detail, "status_code": e.status})


class ConfirmPurchaseInput(BaseModel):
    """Input schema for the confirm purchase tool."""

    request_id: str = Field(description="The request_id from request_purchase")
    success: bool = Field(description="Whether the purchase was successful")
    actual_amount: float | None = Field(
        default=None,
        description="Actual amount spent, if different from requested",
    )


class ConfirmPurchaseTool(BaseTool):
    """LangChain tool that confirms the result of an approved purchase."""

    name: str = "confirm_purchase"
    description: str = (
        "Confirm the result of an approved purchase. "
        "Call AFTER completing (or failing) a purchase to close the request."
    )
    args_schema: type[BaseModel] = ConfirmPurchaseInput

    client: Any = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, token: str | None = None, base_url: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.client = LetAgentPay(token=token, base_url=base_url)

    def _run(
        self,
        request_id: str,
        success: bool,
        actual_amount: float | None = None,
    ) -> str:
        try:
            result = self.client.confirm_purchase(
                request_id,
                success=success,
                actual_amount=actual_amount,
            )
            return json.dumps({
                "request_id": result.request_id,
                "status": result.status,
            })
        except LetAgentPayError as e:
            return json.dumps({"error": e.detail, "status_code": e.status})


# --- Example: Run with a LangChain Agent ---


def main():
    """Run a LangChain agent that uses LetAgentPay for purchase control."""
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate

    # Create LetAgentPay tools — pass token once, share across all tools
    # token/base_url can also be read from LETAGENTPAY_TOKEN env var
    token = None  # or "agt_your_token"
    base_url = None  # or "https://your-instance.com/api/v1/agent-api"
    purchase_tool = LetAgentPayTool(token=token, base_url=base_url)
    budget_tool = CheckBudgetTool(token=token, base_url=base_url)
    categories_tool = ListCategoriesTool(token=token, base_url=base_url)
    confirm_tool = ConfirmPurchaseTool(token=token, base_url=base_url)
    tools = [purchase_tool, budget_tool, categories_tool, confirm_tool]

    # Set up the LLM and agent
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful assistant that can make purchases on behalf of "
            "the user. ALWAYS use the request_purchase tool before making any "
            "purchase. If the request is rejected or pending, inform the user "
            "and do NOT proceed with the purchase. After a successful purchase, "
            "call confirm_purchase with the request_id.",
        ),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Run example tasks
    tasks = [
        "Buy groceries at Whole Foods for $25",
        "Order lunch delivery from Uber Eats for $15",
        "Purchase a $500 laptop from Amazon",
    ]

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print("=" * 60)
        result = executor.invoke({"input": task})
        print(f"\nAgent response: {result['output']}")


if __name__ == "__main__":
    main()
