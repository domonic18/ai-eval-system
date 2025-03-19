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

@contextmanager
def db_operation(db: Session) -> Iterator[Session]:
    """同步数据库会话管理器
    
    Args:
        db: 数据库会话
        
    Yields:
        Session: 活动的数据库会话
    """
    # 如果传入的是可调用对象(如Depends(get_db))，获取实际会话
    if callable(db):
        db = db()
        close_db = True
    else:
        close_db = False
        
    try:
        yield db
    finally:
        if close_db:
            db.close()

# 异步数据库操作的上下文管理器
@asynccontextmanager
async def async_db_operation(db: Union[Session, AsyncSession, Callable]) -> AsyncIterator[Union[Session, AsyncSession]]:
    """异步数据库会话管理器
    
    Args:
        db: 数据库会话或获取会话的函数
        
    Yields:
        Union[Session, AsyncSession]: 活动的数据库会话
    """
    # 处理各种输入类型
    db_session = None
    close_db = False
    
    try:
        if callable(db):
            # 如果是依赖函数
            db_session = db()
            close_db = True
        elif isinstance(db, (AsyncSession, Session)):
            # 如果已经是会话
            db_session = db
        else:
            # 不支持的类型
            raise TypeError(f"不支持的数据库会话类型: {type(db)}")
            
        # 返回活动会话
        yield db_session
        
    except Exception as e:
        # 异常处理
        logger.error(f"异步数据库操作异常: {str(e)}")
        if db_session:
            if isinstance(db_session, AsyncSession):
                await db_session.rollback()
            else:
                db_session.rollback()
        raise
    finally:
        # 确保会话关闭
        if close_db and db_session:
            if isinstance(db_session, AsyncSession):
                await db_session.close()
            else:
                db_session.close()

# 保留 AsyncSessionManager 类用于兼容现有代码，但不再使用
class AsyncSessionManager:
    """异步数据库会话上下文管理器（已弃用，保留为兼容）"""
    
    def __init__(self, db: Union[Session, AsyncSession, Callable]):
        self.db = db
        self.db_session = None
        self.close_db = False
        
    async def __aenter__(self) -> Union[Session, AsyncSession]:
        # 处理各种输入类型
        if callable(self.db):
            # 如果是依赖函数
            self.db_session = self.db()
            self.close_db = True
        elif isinstance(self.db, AsyncSession):
            # 如果已经是异步会话
            self.db_session = self.db
        elif isinstance(self.db, Session):
            # 如果是同步会话，兼容处理
            self.db_session = self.db
        else:
            # 不支持的类型
            raise TypeError(f"不支持的数据库会话类型: {type(self.db)}")
            
        return self.db_session
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 异常处理
            if isinstance(self.db_session, AsyncSession):
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
                
        if self.close_db and self.db_session:
            if isinstance(self.db_session, AsyncSession):
                await self.db_session.close()
            else:
                self.db_session.close()

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