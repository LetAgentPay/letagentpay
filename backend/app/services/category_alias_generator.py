import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def generate_aliases(
    category_name: str,
    display_name: str | None,
    existing_aliases: set[str],
) -> list[str]:
    """Generate alias suggestions for a category using Claude Haiku.

    Returns a list of suggested aliases (lowercase, snake_case),
    filtered to avoid collisions with existing_aliases.
    """
    existing_csv = ", ".join(sorted(existing_aliases)) if existing_aliases else "(none)"
    label = display_name or category_name

    prompt = f"""Generate 5-10 common aliases/synonyms for the purchase category "{category_name}" (display name: "{label}").

Rules:
1. Return only lowercase snake_case aliases, one per line
2. Do NOT include any of these existing names/aliases: {existing_csv}
3. Think of common misspellings, abbreviations, brand names, and synonyms
4. Do NOT include the category name itself ("{category_name}")
5. Return ONLY the aliases, one per line, nothing else"""

    try:
        client = _get_client()
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()  # type: ignore[union-attr]

        aliases = []
        for line in raw.splitlines():
            alias = line.strip().lower().replace(" ", "_").replace("-", "_")
            # Remove leading bullets/numbers
            alias = alias.lstrip("0123456789.-•*) ")
            if alias and alias not in existing_aliases and alias != category_name:
                aliases.append(alias)

        return aliases
    except (
        anthropic.APIError,
        anthropic.APIConnectionError,
        ValueError,
        IndexError,
    ) as e:
        logger.warning("Alias generation failed for '%s': %s", category_name, e)
        return []
