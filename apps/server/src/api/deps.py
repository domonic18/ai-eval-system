from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import db

# 为了向后兼容，保留原来的函数
def get_db():
    """为了依赖注入而提供的获取数据库会话的函数
    
    在FastAPI中使用 Depends(get_db) 来注入会话
    """
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


# from core.database import AsyncSessionLocal
# async def get_db() -> AsyncSession:
#     async with AsyncSessionLocal() as session:
#         yield session