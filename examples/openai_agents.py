#!/usr/bin/env python3
"""OpenAI Agents SDK integration example — LetAgentPay with function calling.

This example shows how to use LetAgentPay with the OpenAI Agents SDK
so that an AI agent checks spending policies before making purchases.

Requirements:
    pip install letagentpay openai-agents

Usage:
    export LETAGENTPAY_TOKEN=agt_<your_token>
    export OPENAI_API_KEY=sk-...
    python examples/openai_agents.py
"""

from __future__ import annotations

import json

from agents import Agent, Runner, function_tool

from letagentpay import LetAgentPay, LetAgentPayError


# --- Tool Definition ---

client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env


@function_tool
def request_purchase(
    amount: float,
    category: str,
    merchant_name: str,
    description: str,
) -> str:
    """Request approval to spend money on a purchase.

    Use this BEFORE making any purchase. The request will be checked
    against spending policies and either auto-approved, sent for review,
    or rejected.

    Args:
        amount: Amount to spend in dollars.
        category: One of: groceries, restaurants, food_delivery, taxi,
            transport, subscriptions, entertainment, education, health,
            electronics, clothing, gas, household, flights, accommodation, other.
        merchant_name: Name of the merchant or service.
        description: What the purchase is for.
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
        return json.dumps(response)
    except LetAgentPayError as e:
        return json.dumps({"error": e.detail, "status_code": e.status})


@function_tool
def check_budget() -> str:
    """Check the current budget status including spent, held, and remaining amounts."""
    try:
        budget = client.check_budget()
        return json.dumps({
            "budget": budget.budget,
            "spent": budget.spent,
            "held": budget.held,
            "remaining": budget.remaining,
            "currency": budget.currency,
        })
    except LetAgentPayError as e:
        return json.dumps({"error": e.detail, "status_code": e.status})


# --- Agent Definition ---

agent = Agent(
    name="Shopping Assistant",
    instructions=(
        "You are a helpful shopping assistant. You can make purchases "
        "on behalf of the user.\n\n"
        "RULES:\n"
        "1. ALWAYS use request_purchase before making any purchase.\n"
        "2. If the request is rejected, explain why and suggest alternatives.\n"
        "3. If the request is pending, tell the user it needs human approval.\n"
        "4. You can check the budget at any time with check_budget.\n"
        "5. Be cost-conscious and suggest cheaper alternatives when appropriate."
    ),
    tools=[request_purchase, check_budget],
)


# --- Run Example ---


async def main():
    """Run the agent with example tasks."""
    tasks = [
        "Buy groceries at Whole Foods for $25",
        "Check my remaining budget",
        "Order a $500 laptop from Amazon",
    ]

    for task in tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        print("=" * 60)
        result = await Runner.run(agent, task)
        print(f"\nAgent: {result.final_output}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
