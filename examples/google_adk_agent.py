#!/usr/bin/env python3
"""Google ADK integration example — LetAgentPay with Agent Development Kit.

This example shows how to use LetAgentPay with Google ADK
so that an AI agent checks spending policies before making purchases.

Requirements:
    pip install letagentpay google-adk

Usage:
    export LETAGENTPAY_TOKEN=agt_<your_token>
    export GOOGLE_API_KEY=...
    python examples/google_adk_agent.py
"""

from __future__ import annotations

import asyncio

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from letagentpay import LetAgentPay, LetAgentPayError


# --- Tool Functions ---

client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env


def request_purchase(
    amount: float,
    category: str,
    merchant_name: str,
    description: str,
) -> dict:
    """Request approval to spend money on a purchase.

    Use this BEFORE making any purchase. The request will be checked
    against spending policies and either auto-approved, sent for review,
    or rejected.

    Args:
        amount: Amount to spend in dollars.
        category: Spending category. Use list_categories to get valid options.
        merchant_name: Name of the merchant or service.
        description: What the purchase is for.

    Returns:
        Dictionary with status, request_id, budget_remaining, and message.
    """
    try:
        result = client.request_purchase(
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
        return response
    except LetAgentPayError as e:
        return {"status": "error", "error": e.detail}


def check_budget() -> dict:
    """Check the current budget status including spent, held, and remaining amounts.

    Returns:
        Dictionary with budget, spent, held, remaining, and currency.
    """
    try:
        budget = client.check_budget()
        return {
            "budget": budget.budget,
            "spent": budget.spent,
            "held": budget.held,
            "remaining": budget.remaining,
            "currency": budget.currency,
        }
    except LetAgentPayError as e:
        return {"status": "error", "error": e.detail}


def list_categories() -> dict:
    """List all valid spending categories for purchase requests.

    Returns:
        Dictionary with a list of valid category strings.
    """
    try:
        categories = client.list_categories()
        return {"categories": categories}
    except LetAgentPayError as e:
        return {"status": "error", "error": e.detail}


def confirm_purchase(
    request_id: str,
    success: bool,
    actual_amount: float | None = None,
) -> dict:
    """Confirm the result of an approved purchase.

    Call this AFTER completing (or failing) a purchase to close the request.

    Args:
        request_id: The request_id from request_purchase.
        success: Whether the purchase was successful.
        actual_amount: Actual amount spent, if different from requested.

    Returns:
        Dictionary with request_id and status.
    """
    try:
        result = client.confirm_purchase(
            request_id,
            success=success,
            actual_amount=actual_amount,
        )
        return {
            "request_id": result.request_id,
            "status": result.status,
        }
    except LetAgentPayError as e:
        return {"status": "error", "error": e.detail}


# --- Agent Definition ---

shopping_agent = Agent(
    model="gemini-2.0-flash",
    name="shopping_assistant",
    description="A shopping assistant that manages purchases within budget policies.",
    instruction=(
        "You are a helpful shopping assistant. You can make purchases "
        "on behalf of the user.\n\n"
        "RULES:\n"
        "1. ALWAYS use request_purchase before making any purchase.\n"
        "2. If the request is rejected, explain why and suggest alternatives.\n"
        "3. If the request is pending, tell the user it needs human approval.\n"
        "4. You can check the budget at any time with check_budget.\n"
        "5. Be cost-conscious and suggest cheaper alternatives when appropriate.\n"
        "6. After a successful purchase, call confirm_purchase with the request_id."
    ),
    tools=[request_purchase, check_budget, list_categories, confirm_purchase],
)


# --- Multi-Agent Example ---
# Each agent gets its own token → separate budget and policies.
# Set RESEARCHER_TOKEN and BUYER_TOKEN env vars, or use the same token for demo.

import os

researcher_client = LetAgentPay(
    token=os.environ.get("RESEARCHER_TOKEN", os.environ.get("LETAGENTPAY_TOKEN", "")),
)


def research_purchase(
    amount: float, category: str, merchant_name: str, description: str
) -> dict:
    """Request purchase approval for research expenses (API calls, data access)."""
    try:
        result = researcher_client.request_purchase(
            amount=amount, category=category,
            merchant_name=merchant_name, description=description,
        )
        return {"status": result.status, "budget_remaining": result.budget_remaining}
    except LetAgentPayError as e:
        return {"status": "error", "error": e.detail}


def research_budget() -> dict:
    """Check the researcher's budget."""
    try:
        budget = researcher_client.check_budget()
        return {"remaining": budget.remaining, "budget": budget.budget}
    except LetAgentPayError as e:
        return {"status": "error", "error": e.detail}


researcher_agent = Agent(
    model="gemini-2.0-flash",
    name="researcher",
    description="Researches products and finds the best deals. Has its own budget.",
    instruction=(
        "You research products and find the best options. "
        "Use research_purchase to check if the budget allows it. "
        "Always check budget first with research_budget."
    ),
    tools=[research_purchase, research_budget],
)

coordinator_agent = Agent(
    model="gemini-2.0-flash",
    name="coordinator",
    description="Coordinates shopping tasks between specialized agents.",
    instruction=(
        "You coordinate shopping tasks. Delegate research to the researcher "
        "agent. Each agent has its own budget — the researcher has a separate "
        "budget for API calls and data access."
    ),
    sub_agents=[researcher_agent],
    tools=[check_budget],
)


# --- Run Example ---


async def main():
    """Run the single-agent example."""
    runner = InMemoryRunner(
        agent=shopping_agent,
        app_name="letagentpay_demo",
    )

    user_id = "demo_user"
    session = await runner.session_service.create_session(
        app_name="letagentpay_demo",
        user_id=user_id,
    )

    tasks = [
        "Check my current budget",
        "Buy groceries at Whole Foods for $25",
        "Order a $500 laptop from Amazon",
    ]

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print("=" * 60)

        message = types.Content(
            role="user",
            parts=[types.Part(text=task)],
        )

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text:
                        print(f"\nAgent: {part.text}")


if __name__ == "__main__":
    asyncio.run(main())
