from datetime import UTC, datetime

from sqlalchemy import ColumnElement, case


def utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC.

    asyncpg returns naive datetimes for TIMESTAMPTZ columns (in UTC but
    without tzinfo). This helper adds UTC tzinfo when missing so that
    comparisons with utcnow() work correctly.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def clamp_zero(expr: ColumnElement):  # type: ignore[type-arg]
    """SQL expression: max(expr, 0), portable across PostgreSQL and SQLite."""
    return case((expr < 0, 0), else_=expr)
