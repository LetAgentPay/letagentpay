from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={
        "server_settings": {
            # Kill sessions stuck in open transactions after 5 min.
            # Prevents idle connections from blocking DDL (ALTER TABLE) during deploys.
            "idle_in_transaction_session_timeout": "300000",  # ms
        }
    },
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session() as session:
        yield session
