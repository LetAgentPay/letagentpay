from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from app.services.category_resolver import (
    CATEGORIES,
    CATEGORY_ALIASES,
    _resolve_via_ai,
    resolve_category,
)


class TestResolveCategory:
    """Tests for resolve_category function."""

    @pytest.mark.parametrize("category", sorted(CATEGORIES))
    async def test_canonical_category_returns_as_is(self, category: str):
        resolved, original = await resolve_category(category)
        assert resolved == category
        assert original is None

    async def test_canonical_uppercase_normalizes(self):
        resolved, original = await resolve_category("GROCERIES")
        assert resolved == "groceries"
        assert original is None

    async def test_canonical_with_spaces_normalizes(self):
        resolved, original = await resolve_category("food delivery")
        assert resolved == "food_delivery"
        assert original is None

    async def test_canonical_with_hyphens_normalizes(self):
        resolved, original = await resolve_category("food-delivery")
        assert resolved == "food_delivery"
        assert original is None

    async def test_alias_software_maps_to_subscriptions(self):
        resolved, original = await resolve_category("software")
        assert resolved == "subscriptions"
        assert original == "software"

    async def test_alias_hotel_maps_to_accommodation(self):
        resolved, original = await resolve_category("hotel")
        assert resolved == "accommodation"
        assert original == "hotel"

    async def test_alias_uber_maps_to_taxi(self):
        resolved, original = await resolve_category("uber")
        assert resolved == "taxi"
        assert original == "uber"

    async def test_alias_case_insensitive(self):
        resolved, original = await resolve_category("SOFTWARE")
        assert resolved == "subscriptions"
        assert original == "SOFTWARE"

    async def test_unknown_category_calls_ai(self):
        with patch(
            "app.services.category_resolver._resolve_via_ai",
            new_callable=AsyncMock,
            return_value="electronics",
        ) as mock_ai:
            resolved, original = await resolve_category("quantum_computer_parts")
            assert resolved == "electronics"
            assert original == "quantum_computer_parts"
            mock_ai.assert_called_once_with("quantum_computer_parts")

    async def test_ai_fallback_returns_other_on_error(self):
        with patch(
            "app.services.category_resolver._resolve_via_ai",
            new_callable=AsyncMock,
            return_value="other",
        ):
            resolved, original = await resolve_category("xyzzy_unknown")
            assert resolved == "other"
            assert original == "xyzzy_unknown"

    async def test_whitespace_stripped(self):
        resolved, original = await resolve_category("  groceries  ")
        assert resolved == "groceries"
        assert original is None

    def test_all_aliases_map_to_valid_categories(self):
        for alias, target in CATEGORY_ALIASES.items():
            assert (
                target in CATEGORIES
            ), f"Alias '{alias}' maps to invalid category '{target}'"


class TestResolveViaAI:
    """Tests for _resolve_via_ai — lines 166-179."""

    async def test_ai_returns_valid_category(self):
        """AI returns a valid category name."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="electronics")]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.category_resolver._get_client", return_value=mock_client
        ):
            result = await _resolve_via_ai("quantum computer parts")
        assert result == "electronics"

    async def test_ai_returns_invalid_category_falls_back(self):
        """AI returns unknown category — falls back to 'other'."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="quantum_stuff")]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.category_resolver._get_client", return_value=mock_client
        ):
            result = await _resolve_via_ai("something weird")
        assert result == "other"

    async def test_ai_exception_falls_back(self):
        """AI call raises exception — falls back to 'other'."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )

        with patch(
            "app.services.category_resolver._get_client", return_value=mock_client
        ):
            result = await _resolve_via_ai("broken input")
        assert result == "other"
