import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

CATEGORIES = {
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

# Static synonym map: alias -> canonical category
CATEGORY_ALIASES: dict[str, str] = {
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

_CATEGORIES_CSV = ", ".join(sorted(CATEGORIES))

_RESOLVE_PROMPT = f"""You are a category classifier. Given a purchase category name, map it to the closest match from this list:

{_CATEGORIES_CSV}

Rules:
1. Return ONLY the category name from the list above, nothing else
2. If the input clearly fits one category, return that category
3. If uncertain or no good match, return "other"
"""

_ai_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _ai_client
    if _ai_client is None:
        _ai_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _ai_client


def _normalize(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


async def _resolve_via_ai(raw: str) -> str:
    """Ask Claude Haiku to classify an unknown category. Returns canonical name."""
    try:
        client = _get_client()
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            system=_RESOLVE_PROMPT,
            messages=[{"role": "user", "content": raw}],
        )
        result = response.content[0].text.strip().lower().replace(" ", "_")  # type: ignore[union-attr]
        if result in CATEGORIES:
            return result
    except (
        anthropic.APIError,
        anthropic.APIConnectionError,
        ValueError,
        IndexError,
    ) as e:
        logger.warning("AI category resolution failed for '%s': %s", raw, e)
    return "other"


async def resolve_category(raw: str) -> tuple[str, str | None]:
    """Resolve raw category to (canonical, original_or_None).

    original is None when the input was already a valid canonical category.
    """
    normalized = _normalize(raw)

    # Exact match
    if normalized in CATEGORIES:
        return normalized, None

    # Static alias
    if normalized in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[normalized], raw

    # AI fallback
    resolved = await _resolve_via_ai(raw)
    return resolved, raw
