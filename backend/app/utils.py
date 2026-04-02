from datetime import UTC, datetime

from sqlalchemy import ColumnElement, case


def utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def clamp_zero(expr: ColumnElement):  # type: ignore[type-arg]
    """SQL expression: max(expr, 0), portable across PostgreSQL and SQLite."""
    return case((expr < 0, 0), else_=expr)
