from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import AsyncSessionLocal
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session