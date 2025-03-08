from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

# 异步数据库引擎（注意使用 asyncmy 驱动）
engine = create_async_engine(
    url=settings.db_url.unicode_string(),
    echo=settings.mysql_debug,  # 调试模式下显示SQL语句
    future=True
)

# 异步会话工厂
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# 声明式基类
Base = declarative_base()

async def get_db() -> AsyncSession:
    """依赖注入用的异步数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session

async def create_tables():
    """创建所有数据表（仅用于开发环境）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
