#!/usr/bin/env python3
"""Stripe + LetAgentPay governance example — policy middleware before payments.

This example shows how LetAgentPay sits between an AI agent and Stripe:
the agent FIRST requests approval from LetAgentPay, and only if approved,
executes the payment via Stripe.

Architecture:
    Agent → LetAgentPay (policy check) → Stripe (payment execution)

Requirements:
    pip install letagentpay stripe openai-agents

Usage:
    export LETAGENTPAY_TOKEN=agt_<your_token>
    export STRIPE_SECRET_KEY=sk_test_...
    export OPENAI_API_KEY=sk-...
    python examples/stripe_governance.py
"""

from __future__ import annotations

import json
import os

import stripe
from agents import Agent, Runner, function_tool

from letagentpay import LetAgentPay, LetAgentPayError


# --- Setup ---

lap_client = LetAgentPay()  # reads LETAGENTPAY_TOKEN from env
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_demo")


# --- Tool 1: Request Permission from LetAgentPay ---


@function_tool
def request_purchase(
    amount: float,
    category: str,
    merchant_name: str,
    description: str,
) -> str:
    """Request approval to spend money on a purchase.

    Use this BEFORE calling execute_payment. The request will be checked
    against spending policies (budget, category limits, daily caps, schedule).

    Args:
        amount: Amount to spend in dollars.
        category: Spending category (e.g. groceries, electronics, subscriptions).
            Unknown categories are auto-mapped to the closest match.
        merchant_name: Name of the merchant or service.
        description: What the purchase is for.
    """
    try:
        result = lap_client.request_purchase(
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
            response["message"] = (
                f"Approved (request_id={result.request_id}). "
                "You may now call execute_payment with this request_id."
            )
        elif result.status == "pending":
            response["message"] = (
                "Pending human review. Do NOT call execute_payment. "
                "Tell the user their purchase needs approval."
            )
        else:
            response["message"] = "Rejected. Find a cheaper alternative."
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


# --- Tool 2: Execute Payment via Stripe (only after LAP approval) ---


@function_tool
def execute_payment(
    request_id: str,
    amount: float,
    description: str,
    customer_email: str,
) -> str:
    """Execute a payment via Stripe. ONLY call this after request_purchase returns 'auto_approved'.

    Args:
        request_id: The request_id from request_purchase (required for verification).
        amount: Amount in dollars (must match the approved amount).
        description: Payment description.
        customer_email: Customer email for the receipt.
    """
    try:
        # Step 1: Verify the request is still approved
        status = lap_client.check_request(request_id)
        if status.status not in ("auto_approved", "approved"):
            return json.dumps({
                "error": f"Request {request_id} is {status.status}, not approved. Cannot pay.",
            })

        # Step 2: Create Stripe PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Stripe uses cents
            currency="usd",
            description=description,
            receipt_email=customer_email,
            metadata={
                "letagentpay_request_id": request_id,
                "agent_managed": "true",
            },
        )

        # Step 3: Report back to LetAgentPay
        lap_client.confirm_purchase(
            request_id,
            success=True,
            actual_amount=amount,
            receipt_url=f"https://dashboard.stripe.com/payments/{intent.id}",
        )

        return json.dumps({
            "status": "payment_created",
            "stripe_payment_id": intent.id,
            "amount": amount,
            "message": f"Payment of ${amount} created successfully.",
        })

    except stripe.StripeError as e:
        # Payment failed — report failure to LetAgentPay
        try:
            lap_client.confirm_purchase(request_id, success=False)
        except LetAgentPayError:
            pass
        return json.dumps({"error": f"Stripe error: {e.user_message}"})
    except LetAgentPayError as e:
        return json.dumps({"error": e.detail, "status_code": e.status})


# --- Tool 3: Budget Check ---


@function_tool
def check_budget() -> str:
    """Check current budget status."""
    try:
        budget = lap_client.check_budget()
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
    name="Governed Payment Agent",
    instructions=(
        "You are a payment assistant with spending governance.\n\n"
        "STRICT RULES:\n"
        "1. ALWAYS call request_purchase FIRST before any payment.\n"
        "2. Only call execute_payment if request_purchase returns 'auto_approved'.\n"
        "3. If request_purchase returns 'pending', tell the user to wait for approval.\n"
        "4. If request_purchase returns 'rejected', explain why and suggest alternatives.\n"
        "5. NEVER call execute_payment without a valid, approved request_id.\n"
        "6. Use check_budget to monitor spending.\n"
        "7. Always pass the request_id from request_purchase to execute_payment."
    ),
    tools=[request_purchase, execute_payment, check_budget],
)


# --- Run Example ---


async def main():
    """Run the governed payment agent."""
    tasks = [
        "Check my budget",
        "Pay $25 to Whole Foods for groceries, receipt to user@example.com",
        "Pay $5000 for a luxury item at Cartier, receipt to user@example.com",
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
