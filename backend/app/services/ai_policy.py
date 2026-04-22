import json
import re

import anthropic

from app.config import settings

_POLICY_SYSTEM_PROMPT_TEMPLATE = """You are a policy configurator for LetAgentPay — a service that manages AI agent spending.

Convert user's natural language rules into a structured JSON policy.

Available fields:
- daily_limit: number (max spending per day)
- weekly_limit: number
- monthly_limit: number
- per_request_limit: number (max single purchase)
- allowed_categories: string[] (from: {categories})
- blocked_categories: string[]
- schedule: {{ timezone: string, default: {{ allow: "HH:MM-HH:MM" }}, overrides: [{{ days: string[], allow?: string, deny?: boolean, daily_limit?: number }}] }}
- auto_approve: {{ enabled: boolean, max_amount?: number, categories?: string[] }}

Rules:
1. Respond with a JSON object with three keys: "policy" (the structured policy), "explanation" (a brief description of what changed in this request, in the same language the user wrote in), and "summary" (a complete human-readable description of ALL rules in the final policy, in the same language the user wrote in — this should describe the full policy, not just the latest change)
2. In "policy", omit fields the user didn't mention (don't guess)
3. Infer timezone from context or default to user's timezone
4. The user may write in any language — understand and convert
5. Return ONLY valid JSON, no markdown fences, no extra text"""

_DEFAULT_CATEGORIES_CSV = "accommodation, clothing, education, electronics, entertainment, flights, food_delivery, gas, groceries, health, household, other, restaurants, subscriptions, taxi, transport"

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling markdown fences."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Last resort: find first { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end != -1:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from AI response: {text[:200]}")


async def convert_text_to_policy(
    message: str,
    chat_history: list[dict] | None = None,
    user_timezone: str = "America/New_York",
    current_policy: dict | None = None,
    account_categories: list[str] | None = None,
) -> dict:
    """Convert natural language to structured policy JSON via Claude API.

    Returns {"policy": {...}, "explanation": "..."}.
    Raises ValueError if AI response cannot be parsed.
    """
    client = _get_client()

    categories_csv = (
        ", ".join(sorted(account_categories))
        if account_categories
        else _DEFAULT_CATEGORIES_CSV
    )
    system = _POLICY_SYSTEM_PROMPT_TEMPLATE.format(categories=categories_csv)
    system += f"\n\nUser's timezone: {user_timezone}"

    if current_policy:
        system += f"\n\nThe agent already has this policy configured:\n{json.dumps(current_policy, indent=2)}\n\nIMPORTANT: The user wants to UPDATE the existing policy, not replace it. Merge the new rules with the existing ones. Keep all existing rules that the user did not mention. Only change or add what the user explicitly asked for."

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": message})

    response = await client.messages.create(
        model=settings.ai_model,
        max_tokens=1024,
        system=system,
        messages=messages,  # type: ignore[arg-type]
    )

    raw = response.content[0].text  # type: ignore[union-attr]
    return _extract_json(raw)
