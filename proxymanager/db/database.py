from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base
from ..core.config import config

DATABASE_URL = config.get("database_url")

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    """Creates database tables from the models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
