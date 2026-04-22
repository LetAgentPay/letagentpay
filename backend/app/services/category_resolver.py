import logging

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Category, CategoryAlias

logger = logging.getLogger(__name__)

# Default categories and aliases — used by import-defaults endpoint
DEFAULT_CATEGORIES = {
    "accommodation",
    "clothing",
    "education",
    "electronics",
    "entertainment",
    "flights",
    "food_delivery",
    "gas",
    "groceries",
    "health",
    "household",
    "other",
    "restaurants",
    "subscriptions",
    "taxi",
    "transport",
}

DEFAULT_CATEGORY_ALIASES: dict[str, str] = {
    # food_delivery
    "food": "food_delivery",
    "delivery": "food_delivery",
    "uber_eats": "food_delivery",
    "doordash": "food_delivery",
    "grubhub": "food_delivery",
    "takeout": "food_delivery",
    "takeaway": "food_delivery",
    # restaurants
    "dining": "restaurants",
    "restaurant": "restaurants",
    "cafe": "restaurants",
    "coffee": "restaurants",
    "bar": "restaurants",
    "lunch": "restaurants",
    "dinner": "restaurants",
    # groceries
    "grocery": "groceries",
    "supermarket": "groceries",
    "market": "groceries",
    "food_store": "groceries",
    # transport
    "transportation": "transport",
    "transit": "transport",
    "bus": "transport",
    "train": "transport",
    "metro": "transport",
    "subway": "transport",
    "public_transport": "transport",
    # taxi
    "uber": "taxi",
    "lyft": "taxi",
    "ride": "taxi",
    "rideshare": "taxi",
    "cab": "taxi",
    # flights
    "flight": "flights",
    "airfare": "flights",
    "airline": "flights",
    "air_travel": "flights",
    "plane": "flights",
    # accommodation
    "hotel": "accommodation",
    "lodging": "accommodation",
    "airbnb": "accommodation",
    "hostel": "accommodation",
    "motel": "accommodation",
    "booking": "accommodation",
    # subscriptions
    "subscription": "subscriptions",
    "software": "subscriptions",
    "saas": "subscriptions",
    "license": "subscriptions",
    "membership": "subscriptions",
    "app": "subscriptions",
    # electronics
    "tech": "electronics",
    "gadgets": "electronics",
    "hardware": "electronics",
    "computer": "electronics",
    "devices": "electronics",
    "phone": "electronics",
    # entertainment
    "movies": "entertainment",
    "games": "entertainment",
    "gaming": "entertainment",
    "music": "entertainment",
    "streaming": "entertainment",
    "cinema": "entertainment",
    "concert": "entertainment",
    # education
    "learning": "education",
    "course": "education",
    "courses": "education",
    "training": "education",
    "books": "education",
    "book": "education",
    "tutorial": "education",
    # health
    "medical": "health",
    "pharmacy": "health",
    "medicine": "health",
    "doctor": "health",
    "healthcare": "health",
    "wellness": "health",
    "fitness": "health",
    "gym": "health",
    # clothing
    "clothes": "clothing",
    "apparel": "clothing",
    "shoes": "clothing",
    "fashion": "clothing",
    # gas
    "fuel": "gas",
    "gasoline": "gas",
    "petrol": "gas",
    # household
    "home": "household",
    "furniture": "household",
    "appliances": "household",
    "cleaning": "household",
    "utilities": "household",
    # other
    "misc": "other",
    "miscellaneous": "other",
    "general": "other",
}

_ai_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _ai_client
    if _ai_client is None:
        _ai_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _ai_client


def _normalize(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


async def _get_account_categories(db: AsyncSession, account_id: str) -> set[str]:
    """Get active category names for an account."""
    result = await db.execute(
        select(Category.name).where(
            Category.account_id == account_id, Category.is_active.is_(True)
        )
    )
    return {row[0] for row in result.all()}


async def _get_account_aliases(db: AsyncSession, account_id: str) -> dict[str, str]:
    """Get alias→category_name mapping for an account."""
    result = await db.execute(
        select(CategoryAlias.alias, Category.name)
        .join(Category, CategoryAlias.category_id == Category.id)
        .where(
            CategoryAlias.account_id == account_id,
            Category.is_active.is_(True),
        )
    )
    return {row[0]: row[1] for row in result.all()}


async def _resolve_via_ai(raw: str, categories: set[str]) -> str | None:
    """Ask Claude Haiku to classify against a dynamic category list.

    Returns canonical name if confident, None otherwise.
    """
    if not categories:
        return None

    categories_csv = ", ".join(sorted(categories))
    system_prompt = f"""You are a category classifier. Given a purchase category name, map it to the closest match from this list:

{categories_csv}

Rules:
1. Return ONLY the category name from the list above, nothing else
2. If the input clearly fits one category, return that category
3. If uncertain or no good match, return "other"
"""

    try:
        client = _get_client()
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            system=system_prompt,
            messages=[{"role": "user", "content": raw}],
        )
        result = response.content[0].text.strip().lower().replace(" ", "_")  # type: ignore[union-attr]
        if result in categories:
            return result
    except (
        anthropic.APIError,
        anthropic.APIConnectionError,
        ValueError,
        IndexError,
    ) as e:
        logger.warning("AI category resolution failed for '%s': %s", raw, e)
    return None


async def resolve_category(
    raw: str, account_id: str, db: AsyncSession
) -> tuple[str, str | None, str | None]:
    """Resolve raw category to (canonical, original_or_None, category_status).

    category_status is None for resolved, "unresolved" for orphan.
    """
    normalized = _normalize(raw)

    # Load account's categories and aliases
    categories = await _get_account_categories(db, account_id)
    aliases = await _get_account_aliases(db, account_id)

    # Exact match against account categories
    if normalized in categories:
        return normalized, None, None

    # Alias match
    if normalized in aliases:
        return aliases[normalized], raw, None

    # Account has no categories at all — everything is orphan
    if not categories:
        return "other", raw, "unresolved"

    # AI fallback with account's category list
    ai_result = await _resolve_via_ai(raw, categories)
    if ai_result:
        return ai_result, raw, None

    # Orphan — use "other" for policy checks, flag as unresolved
    return "other", raw, "unresolved"
