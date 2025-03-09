#!/usr/bin/env python3
# 数据库工具模块

import logging
import contextlib
from typing import Union, Iterator, Optional, TypeVar, Callable, Any, AsyncIterator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import SessionLocal
import asyncio
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')

class DatabaseSessionManager:
    """数据库会话管理器
    
    提供同步和异步数据库会话的上下文管理器支持，
    简化数据库会话的获取和释放过程。
    """
    
    @staticmethod
    @contextmanager
    def session() -> Iterator[Session]:
        """获取数据库会话的上下文管理器
        
        用法:
            with DatabaseSessionManager.session() as db:
                # 使用db进行数据库操作
                
        确保在退出上下文时自动关闭会话
        """
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作异常，已回滚: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    @asynccontextmanager
    async def async_session() -> AsyncIterator[Session]:
        """获取异步数据库会话的上下文管理器
        
        用法:
            async with DatabaseSessionManager.async_session() as db:
                # 使用db进行异步数据库操作
                
        确保在退出上下文时自动关闭会话
        """
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            await asyncio.to_thread(db.rollback)
            logger.error(f"异步数据库操作异常，已回滚: {str(e)}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def execute_with_session(func: Callable[[Session], T]) -> T:
        """使用数据库会话执行函数
        
        Args:
            func: 接受数据库会话作为参数的函数
            
        Returns:
            函数执行的结果
            
        用法:
            result = DatabaseSessionManager.execute_with_session(
                lambda db: db.query(User).filter(User.id == 1).first()
            )
        """
        with DatabaseSessionManager.session() as db:
            return func(db)
    
    @staticmethod
    async def execute_with_async_session(func: Callable[[Session], T]) -> T:
        """使用异步数据库会话执行函数
        
        Args:
            func: 接受数据库会话作为参数的函数
            
        Returns:
            函数执行的结果
            
        用法:
            result = await DatabaseSessionManager.execute_with_async_session(
                lambda db: db.query(User).filter(User.id == 1).first()
            )
        """
        async with DatabaseSessionManager.async_session() as db:
            return await asyncio.to_thread(func, db)

# 兼容现有代码的辅助函数
@contextmanager
def get_db_session() -> Iterator[Session]:
    """获取数据库会话的上下文管理器（兼容接口）
    
    用法:
        with get_db_session() as db:
            # 使用db进行数据库操作
    """
    with DatabaseSessionManager.session() as db:
        yield db

# 数据库会话上下文管理器
@contextmanager
def db_operation(db_or_func=None):
    """数据库会话上下文管理器
    
    支持两种用法:
    1. 传入现有db会话:
       with db_operation(db) as session:
           # 使用session进行操作
    
    2. 不传参数，自动创建会话:
       with db_operation() as session:
           # 使用session进行操作
    """
    if hasattr(db_or_func, 'close'):  # 已经是数据库会话
        yield db_or_func
    else:  # 需要创建新会话
        with DatabaseSessionManager.session() as session:
            yield session

# 异步数据库操作的上下文管理器
@asynccontextmanager
async def async_db_operation(db_or_func=None):
    """异步数据库操作上下文管理器
    
    支持两种用法:
    1. 传入现有db会话:
       async with async_db_operation(db) as session:
           # 使用session进行操作
    
    2. 不传参数，自动创建会话:
       async with async_db_operation() as session:
           # 使用session进行操作
    """
    if hasattr(db_or_func, 'close'):  # 已经是数据库会话
        yield db_or_func
    else:  # 需要创建新会话
        async with DatabaseSessionManager.async_session() as session:
            yield session

def with_db_session(func: Callable[..., T]) -> Callable[..., T]:
    """数据库会话装饰器
    
    自动管理函数中的数据库会话资源
    
    Args:
        func: 要装饰的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    def wrapper(db: Union[Session, Iterator[Session], None] = None, *args, **kwargs) -> T:
        with db_operation(db) as session:
            return func(session, *args, **kwargs)
    return wrapper 