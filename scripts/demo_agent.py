#!/usr/bin/env python3
"""Demo agent — sends test purchase requests to LetAgentPay API using the SDK.

Usage:
    pip install letagentpay

    python scripts/demo_agent.py --token agt_<your_token>
    python scripts/demo_agent.py --token agt_<your_token> --base-url https://api.letagentpay.com
    python scripts/demo_agent.py --token agt_<your_token> --mode burst
    python scripts/demo_agent.py --token agt_<your_token> --mode interactive

Modes:
    burst       — send 5 random requests quickly (default)
    continuous  — send a request every 10-30 seconds until stopped
    interactive — choose amount/category manually
"""

import argparse
import random
import sys
import time

from letagentpay import LetAgentPay, LetAgentPayError

SAMPLE_REQUESTS = [
    {"amount": 4.99, "category": "food_delivery", "merchant_name": "Uber Eats", "description": "Lunch delivery"},
    {"amount": 12.50, "category": "taxi", "merchant_name": "Uber", "description": "Ride to office"},
    {"amount": 29.99, "category": "subscriptions", "merchant_name": "Netflix", "description": "Monthly subscription"},
    {"amount": 8.75, "category": "groceries", "merchant_name": "Whole Foods", "description": "Snacks"},
    {"amount": 45.00, "category": "restaurants", "merchant_name": "Sushi Place", "description": "Team dinner"},
    {"amount": 15.00, "category": "transport", "merchant_name": "Metro", "description": "Weekly pass"},
    {"amount": 99.00, "category": "electronics", "merchant_name": "Amazon", "description": "USB-C hub"},
    {"amount": 5.99, "category": "entertainment", "merchant_name": "Spotify", "description": "Music streaming"},
    {"amount": 22.00, "category": "health", "merchant_name": "CVS Pharmacy", "description": "Vitamins"},
    {"amount": 35.00, "category": "clothing", "merchant_name": "Uniqlo", "description": "T-shirt"},
    {"amount": 50.00, "category": "gas", "merchant_name": "Shell", "description": "Full tank"},
    {"amount": 18.99, "category": "household", "merchant_name": "Target", "description": "Cleaning supplies"},
    {"amount": 7.50, "category": "education", "merchant_name": "Coursera", "description": "Course payment"},
    {"amount": 3.25, "category": "other", "merchant_name": "Vending Machine", "description": "Coffee"},
]


def show_budget(client: LetAgentPay):
    """Display current budget info."""
    try:
        b = client.check_budget()
        print(f"  Budget: ${b.budget} | Spent: ${b.spent} | Held: ${b.held} | Remaining: ${b.remaining}")
    except LetAgentPayError as e:
        print(f"  Budget error: [{e.status}] {e.detail}")


def send_request(client: LetAgentPay, data: dict) -> str | None:
    """Send a purchase request. Returns request_id if successful."""
    print(f"  Sending: ${data['amount']} — {data['category']} ({data.get('merchant_name', 'N/A')})")
    try:
        result = client.request_purchase(**data)
        marker = {"auto_approved": "AUTO", "pending": "PENDING", "rejected": "REJECTED"}.get(
            result.status, result.status
        )
        print(f"  Result: [{marker}] request_id={result.request_id}")
        if result.policy_check:
            for check in result.policy_check.checks:
                if check.result == "fail":
                    print(f"    FAIL: {check.rule} — {check.detail}")
        if result.budget_remaining is not None:
            print(f"  Budget remaining: ${result.budget_remaining}")

        # Auto-confirm approved purchases
        if result.status == "auto_approved":
            actual = round(data["amount"] * random.uniform(0.95, 1.0), 2)
            confirm = client.confirm_purchase(result.request_id, success=True, actual_amount=actual)
            print(f"  Confirmed: ${actual} → {confirm.status}")

        return result.request_id
    except LetAgentPayError as e:
        print(f"  ERROR [{e.status}]: {e.detail}")
        return None


def mode_burst(client: LetAgentPay, count: int = 5):
    """Send several random requests quickly."""
    print(f"\n--- Burst mode: sending {count} requests ---\n")
    show_budget(client)
    print()

    samples = random.sample(SAMPLE_REQUESTS, min(count, len(SAMPLE_REQUESTS)))
    for i, req_data in enumerate(samples, 1):
        print(f"[{i}/{count}]")
        send_request(client, req_data)
        print()
        if i < count:
            time.sleep(1)

    print("--- Done ---")
    show_budget(client)

    # Show recent requests
    print("\n--- Recent requests ---")
    try:
        req_list = client.my_requests(limit=count)
        for req in req_list.requests:
            print(f"  {req.request_id[:8]}… ${req.amount} [{req.status}] {req.category}")
    except LetAgentPayError as e:
        print(f"  Error: [{e.status}] {e.detail}")


def mode_continuous(client: LetAgentPay):
    """Send random requests at intervals until interrupted."""
    print("\n--- Continuous mode (Ctrl+C to stop) ---\n")
    show_budget(client)
    print()

    count = 0
    try:
        while True:
            count += 1
            req_data = random.choice(SAMPLE_REQUESTS)
            print(f"[#{count}]")
            send_request(client, req_data)
            print()
            delay = random.randint(10, 30)
            print(f"  Next request in {delay}s...")
            time.sleep(delay)
    except KeyboardInterrupt:
        print(f"\n\n--- Stopped after {count} requests ---")
        show_budget(client)


def mode_interactive(client: LetAgentPay):
    """Manually enter request details."""
    print("\n--- Interactive mode (type 'quit' to exit) ---\n")
    show_budget(client)

    try:
        categories = client.list_categories()
        print(f"  Categories: {', '.join(categories)}")
    except LetAgentPayError:
        pass

    print()

    while True:
        try:
            amount_str = input("Amount ($): ").strip()
            if amount_str.lower() == "quit":
                break
            category = input("Category: ").strip()
            merchant = input("Merchant (optional): ").strip() or None
            description = input("Description (optional): ").strip() or None

            data: dict = {"amount": float(amount_str), "category": category}
            if merchant:
                data["merchant_name"] = merchant
            if description:
                data["description"] = description

            print()
            send_request(client, data)
            print()

        except (KeyboardInterrupt, EOFError):
            break
        except ValueError:
            print("  Invalid amount.\n")
            continue

    print("\n--- Done ---")
    show_budget(client)


def main():
    parser = argparse.ArgumentParser(description="LetAgentPay demo agent (uses letagentpay SDK)")
    parser.add_argument("--token", required=True, help="Agent bearer token (agt_...)")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend URL (default: http://localhost:8000, prod: https://api.letagentpay.com)",
    )
    parser.add_argument("--mode", choices=["burst", "continuous", "interactive"], default="burst")
    parser.add_argument("--count", type=int, default=5, help="Number of requests in burst mode")
    args = parser.parse_args()

    api_url = f"{args.base_url}/api/v1/agent-api"
    print("LetAgentPay Demo Agent (SDK)")
    print(f"API: {api_url}")
    print(f"Mode: {args.mode}")

    client = LetAgentPay(token=args.token, base_url=api_url)

    try:
        if args.mode == "burst":
            mode_burst(client, args.count)
        elif args.mode == "continuous":
            mode_continuous(client)
        elif args.mode == "interactive":
            mode_interactive(client)
    finally:
        client.close()


if __name__ == "__main__":
    main()
