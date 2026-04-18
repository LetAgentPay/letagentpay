#!/usr/bin/env python3
"""CrewAI integration example — LetAgentPay with CrewAI agents.

This example shows how to create a CrewAI agent that uses LetAgentPay
to check spending policies before making purchases.

Requirements:
    pip install letagentpay crewai crewai-tools

Usage:
    export LETAGENTPAY_TOKEN=agt_<your_token>
    export OPENAI_API_KEY=sk-...
    python examples/crewai_agent.py
"""

from __future__ import annotations

import json

from crewai import Agent, Crew, Task
from crewai.tools import tool

from letagentpay import LetAgentPay, LetAgentPayError


# --- Tool Definitions ---

client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env


@tool("Request Purchase")
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
        category: Spending category (e.g. groceries, electronics, subscriptions).
            Use List Categories to get valid options. Unknown categories are auto-mapped.
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


@tool("Check Budget")
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


@tool("List Categories")
def list_categories() -> str:
    """List valid spending categories for purchase requests."""
    try:
        categories = client.list_categories()
        return json.dumps({"categories": categories})
    except LetAgentPayError as e:
        return json.dumps({"error": e.detail, "status_code": e.status})


@tool("Confirm Purchase")
def confirm_purchase(
    request_id: str,
    success: bool,
    actual_amount: float | None = None,
) -> str:
    """Confirm the result of an approved purchase.

    Call this AFTER completing (or failing) a purchase to close the request.

    Args:
        request_id: The request_id from Request Purchase.
        success: Whether the purchase was successful.
        actual_amount: Actual amount spent, if different from requested.
    """
    try:
        result = client.confirm_purchase(
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


# --- CrewAI Agent & Task ---

shopping_agent = Agent(
    role="Shopping Assistant",
    goal="Complete purchase tasks while staying within budget and policy limits",
    backstory=(
        "You are a responsible shopping assistant that always checks "
        "spending policies before making any purchase. You never proceed "
        "with a purchase that was rejected or is still pending review. "
        "After completing a purchase, you always confirm it."
    ),
    tools=[request_purchase, check_budget, list_categories, confirm_purchase],
    verbose=True,
)


def main():
    """Run a CrewAI crew with budget-controlled purchasing tasks."""
    shopping_task = Task(
        description=(
            "Complete the following shopping list:\n"
            "1. Buy groceries at Whole Foods (~$25)\n"
            "2. Order lunch delivery from Uber Eats (~$15)\n"
            "3. Purchase office supplies from Amazon (~$40)\n\n"
            "For each item:\n"
            "- Request purchase approval first\n"
            "- If approved, confirm the purchase\n"
            "- If rejected, note the reason and skip\n"
            "- If pending, note that it needs human review\n"
            "After all items, check the remaining budget."
        ),
        expected_output=(
            "A summary of all purchase attempts with their status "
            "(approved/rejected/pending) and the final budget status."
        ),
        agent=shopping_agent,
    )

    crew = Crew(
        agents=[shopping_agent],
        tasks=[shopping_task],
        verbose=True,
    )

    result = crew.kickoff()
    print(f"\n{'='*60}")
    print("Final Result:")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
