
# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from dotenv import load_dotenv
# import os
# from typing import Generator
# from apps.server.src.core.config import DB_URL, settings
# from urllib import parse


# import logging

# # 配置根日志记录器
# logging.basicConfig(level=logging.WARNING)

# # 设置 SQLAlchemy 日志级别
# sqlalchemy_logger = logging.getLogger('sqlalchemy')
# sqlalchemy_logger.setLevel(logging.WARNING)

# # 移除所有现有的处理器
# for handler in sqlalchemy_logger.handlers[:]:
#     sqlalchemy_logger.removeHandler(handler)

# # 设置引擎日志级别
# engine_logger = logging.getLogger('sqlalchemy.engine')
# engine_logger.setLevel(logging.WARNING)

# # 移除所有现有的处理器
# for handler in engine_logger.handlers[:]:
#     engine_logger.removeHandler(handler)

# # 加载环境变量
# load_dotenv()

# # 创建基类
# Base = declarative_base()

# class Database:
#     def __init__(self):
#         # 获取数据库URL
#         self.DATABASE_URL = os.getenv("DB_URL", DB_URL)
        
#         # 添加调试输出
#         print(f"当前数据库连接URL: {self.DATABASE_URL}")
#         print(f"解析后的连接参数: {parse.urlparse(self.DATABASE_URL)}")
        
#         # 创建引擎
#         self.engine = create_engine(
#             self.DATABASE_URL, 
#             # MySQL连接参数
#             pool_size=5,  # 连接池大小
#             max_overflow=10,  # 超出连接池大小后可以创建的连接数
#             pool_timeout=30,  # 等待连接的超时时间（秒）
#             pool_recycle=1800,  # 连接重置周期（秒）
#             echo=settings.debug,  # 调试模式下打印SQL语句
#         )
        
#         # 创建会话工厂
#         self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
#     def get_db(self) -> Generator:
#         """获取数据库会话，使用后自动关闭"""
#         db = self.SessionLocal()
#         try:
#             yield db
#         finally:
#             db.close()
    
#     def create_tables(self):
#         """创建所有表"""
#         try:
#             Base.metadata.create_all(bind=self.engine)
#             print(f"✅ 成功创建表结构，当前数据库：{self.DATABASE_URL}")
#         except Exception as e:
#             print(f"❌ 创建表失败: {str(e)}")
#             raise
    
#     def drop_tables(self):
#         """删除所有表（谨慎使用）"""
#         Base.metadata.drop_all(bind=self.engine)

# # 创建全局数据库实例
# db = Database()

# # 为了向后兼容，保留原来的函数
# def get_db():
#     """为了依赖注入而提供的获取数据库会话的函数
    
#     在FastAPI中使用 Depends(get_db) 来注入会话
#     """
#     db_session = db.SessionLocal()
#     try:
#         yield db_session
#     finally:
#         db_session.close()

# # 为了向后兼容，提供模块级别的SessionLocal
# SessionLocal = db.SessionLocal

# # 导出engine对象以便main.py可以导入
# engine = db.engine 



# # 异步数据库引擎（注意使用 asyncmy 驱动）
# engine = create_async_engine(
#     url=settings.db_url.unicode_string(),
#     echo=settings.mysql_debug,  # 调试模式下显示SQL语句
#     future=True
# )

# # 异步会话工厂
# AsyncSessionLocal = sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
#     autoflush=False
# )

# async def get_db() -> AsyncSession:
#     """依赖注入用的异步数据库会话"""
#     async with AsyncSessionLocal() as session:
#         yield session

# async def create_tables():
#     """创建所有数据表（仅用于开发环境）"""
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)


# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import Column, DateTime, text  # 新增关键导入
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
from urllib import parse
from core.config import settings






# 声明式基类
Base = declarative_base()

class TimestampMixin:
    """自动时间戳 Mixin 类（需要被模型继承）"""
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP")  # 更新时自动触发
    )


class Database:
    def __init__(self):
        # 获取数据库URL
        self.DATABASE_URL = settings.db_url.unicode_string()
        
        # 添加调试输出
        print(f"当前数据库连接URL: {self.DATABASE_URL}")
        print(f"解析后的连接参数: {parse.urlparse(self.DATABASE_URL)}")
        
        # 创建引擎
        self.engine = create_engine(
            self.DATABASE_URL, 
            # MySQL连接参数
            pool_size=5,  # 连接池大小
            max_overflow=10,  # 超出连接池大小后可以创建的连接数
            pool_timeout=30,  # 等待连接的超时时间（秒）
            pool_recycle=1800,  # 连接重置周期（秒）
            echo=settings.mysql_debug,  # 调试模式下打印SQL语句
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_db(self) -> Generator:
        """获取数据库会话，使用后自动关闭"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def create_tables(self):
        """创建所有表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print(f"✅ 成功创建表结构，当前数据库：{self.DATABASE_URL}")
        except Exception as e:
            print(f"❌ 创建表失败: {str(e)}")
            raise
    
    def drop_tables(self):
        """删除所有表（谨慎使用）"""
        Base.metadata.drop_all(bind=self.engine)

# 创建全局数据库实例
db = Database()

# 为了向后兼容，提供模块级别的SessionLocal
SessionLocal = db.SessionLocal

# 导出engine对象以便main.py可以导入
engine = db.engine 