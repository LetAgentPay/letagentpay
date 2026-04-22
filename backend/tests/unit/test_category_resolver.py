from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

from app.services.category_resolver import (
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ALIASES,
    _resolve_via_ai,
    resolve_category,
)


def _mock_db(categories: set[str], aliases: dict[str, str] | None = None):
    """Create a mock db session that returns given categories and aliases."""
    db = AsyncMock()

    async def mock_execute(query):
        result = MagicMock()
        query_str = str(query)
        if "category_aliases" in query_str or "CategoryAlias" in query_str:
            # Alias query returns (alias, category_name) tuples
            rows = list((aliases or {}).items())
            result.all.return_value = rows
        else:
            # Category query returns (name,) tuples
            result.all.return_value = [(c,) for c in categories]
        return result

    db.execute = mock_execute
    return db


class TestResolveCategory:
    """Tests for resolve_category function (per-account)."""

    async def test_canonical_category_returns_as_is(self):
        db = _mock_db({"groceries", "other"})
        resolved, original, status = await resolve_category("groceries", "acc1", db)
        assert resolved == "groceries"
        assert original is None
        assert status is None

    async def test_canonical_uppercase_normalizes(self):
        db = _mock_db({"groceries", "other"})
        resolved, original, status = await resolve_category("GROCERIES", "acc1", db)
        assert resolved == "groceries"
        assert original is None
        assert status is None

    async def test_canonical_with_spaces_normalizes(self):
        db = _mock_db({"food_delivery", "other"})
        resolved, original, status = await resolve_category("food delivery", "acc1", db)
        assert resolved == "food_delivery"
        assert original is None
        assert status is None

    async def test_canonical_with_hyphens_normalizes(self):
        db = _mock_db({"food_delivery", "other"})
        resolved, original, status = await resolve_category("food-delivery", "acc1", db)
        assert resolved == "food_delivery"
        assert original is None
        assert status is None

    async def test_alias_resolves(self):
        db = _mock_db(
            {"subscriptions", "other"},
            {"software": "subscriptions"},
        )
        resolved, original, status = await resolve_category("software", "acc1", db)
        assert resolved == "subscriptions"
        assert original == "software"
        assert status is None

    async def test_alias_case_insensitive(self):
        db = _mock_db(
            {"subscriptions", "other"},
            {"software": "subscriptions"},
        )
        resolved, original, status = await resolve_category("SOFTWARE", "acc1", db)
        assert resolved == "subscriptions"
        assert original == "SOFTWARE"
        assert status is None

    async def test_unknown_category_calls_ai(self):
        db = _mock_db({"electronics", "other"})
        with patch(
            "app.services.category_resolver._resolve_via_ai",
            new_callable=AsyncMock,
            return_value="electronics",
        ) as mock_ai:
            resolved, original, status = await resolve_category(
                "quantum_computer_parts", "acc1", db
            )
            assert resolved == "electronics"
            assert original == "quantum_computer_parts"
            assert status is None
            mock_ai.assert_called_once_with(
                "quantum_computer_parts", {"electronics", "other"}
            )

    async def test_orphan_when_ai_returns_none(self):
        db = _mock_db({"electronics", "other"})
        with patch(
            "app.services.category_resolver._resolve_via_ai",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resolved, original, status = await resolve_category(
                "xyzzy_unknown", "acc1", db
            )
            assert resolved == "other"
            assert original == "xyzzy_unknown"
            assert status == "unresolved"

    async def test_empty_categories_returns_orphan(self):
        db = _mock_db(set())
        resolved, original, status = await resolve_category("anything", "acc1", db)
        assert resolved == "other"
        assert original == "anything"
        assert status == "unresolved"

    async def test_whitespace_stripped(self):
        db = _mock_db({"groceries", "other"})
        resolved, original, status = await resolve_category("  groceries  ", "acc1", db)
        assert resolved == "groceries"
        assert original is None
        assert status is None

    def test_all_default_aliases_map_to_valid_categories(self):
        for alias, target in DEFAULT_CATEGORY_ALIASES.items():
            assert (
                target in DEFAULT_CATEGORIES
            ), f"Default alias '{alias}' maps to invalid category '{target}'"


class TestResolveViaAI:
    """Tests for _resolve_via_ai with dynamic category list."""

    async def test_ai_returns_valid_category(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="electronics")]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        categories = {"electronics", "other", "groceries"}
        with patch(
            "app.services.category_resolver._get_client", return_value=mock_client
        ):
            result = await _resolve_via_ai("quantum computer parts", categories)
        assert result == "electronics"

    async def test_ai_returns_invalid_category_returns_none(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="quantum_stuff")]
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        categories = {"electronics", "other"}
        with patch(
            "app.services.category_resolver._get_client", return_value=mock_client
        ):
            result = await _resolve_via_ai("something weird", categories)
        assert result is None

    async def test_ai_exception_returns_none(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.APIConnectionError(request=MagicMock())
        )

        categories = {"electronics", "other"}
        with patch(
            "app.services.category_resolver._get_client", return_value=mock_client
        ):
            result = await _resolve_via_ai("broken input", categories)
        assert result is None

    async def test_ai_with_empty_categories_returns_none(self):
        result = await _resolve_via_ai("anything", set())
        assert result is None
