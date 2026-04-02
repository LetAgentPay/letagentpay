"""Tests for AI policy JSON extraction (no actual API calls)."""

import pytest

from app.services.ai_policy import _extract_json


class TestExtractJson:
    def test_plain_json(self):
        text = '{"policy": {"daily_limit": 5000}, "explanation": "test"}'
        result = _extract_json(text)
        assert result["policy"]["daily_limit"] == 5000

    def test_with_code_fences(self):
        text = '```json\n{"policy": {"daily_limit": 3000}, "explanation": "ok"}\n```'
        result = _extract_json(text)
        assert result["policy"]["daily_limit"] == 3000

    def test_with_code_fences_no_lang(self):
        text = '```\n{"policy": {}, "explanation": "empty"}\n```'
        result = _extract_json(text)
        assert result["explanation"] == "empty"

    def test_with_surrounding_text(self):
        text = 'Here is the policy:\n{"policy": {"daily_limit": 1000}, "explanation": "x"}\nEnd.'
        result = _extract_json(text)
        assert result["policy"]["daily_limit"] == 1000

    def test_with_whitespace(self):
        text = '  \n  {"policy": {}, "explanation": "ws"}  \n  '
        result = _extract_json(text)
        assert result["explanation"] == "ws"

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            _extract_json("this is not json at all")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            _extract_json("")

    def test_nested_braces(self):
        text = '{"policy": {"schedule": {"default": {"allow": "07:00-23:00"}}}, "explanation": "nested"}'
        result = _extract_json(text)
        assert result["policy"]["schedule"]["default"]["allow"] == "07:00-23:00"

    def test_code_fence_with_invalid_json_falls_through(self):
        """Lines 54-55: code fence match but invalid JSON inside, falls to brace search."""
        text = '```json\nnot valid json\n```\n{"policy": {}, "explanation": "fallback"}'
        result = _extract_json(text)
        assert result["explanation"] == "fallback"

    def test_brace_block_invalid_json_raises(self):
        """Lines 63-64: brace block found but invalid JSON inside."""
        text = "prefix { not: valid json } suffix"
        with pytest.raises(ValueError, match="Could not parse JSON"):
            _extract_json(text)

    def test_no_braces_raises(self):
        """No braces at all in text."""
        with pytest.raises(ValueError, match="Could not parse JSON"):
            _extract_json("no braces here at all")
