#!/usr/bin/env python3
# 数据库工具模块

import logging
import contextlib
from typing import Union, Iterator, Optional, TypeVar, Callable, Any, AsyncIterator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
# from core.database import SessionLocal
import asyncio
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')

def get_db_session(db: Union[Session, Iterator[Session], None] = None) -> tuple[Session, bool]:
    """获取数据库会话
    
    如果提供了会话则直接使用，否则创建新会话
    
    Args:
        db: 可选的数据库会话对象或生成器
        
    Returns:
        tuple[Session, bool]: 会话对象和是否需要关闭的标志
    """
    if db is not None:
        # 直接使用提供的会话，不需要额外处理
        if isinstance(db, Iterator):
            try:
                return next(db), False
            except StopIteration:
                # 如果迭代器已耗尽，创建新会话
                logger.warning("提供的数据库会话迭代器已耗尽，创建新会话")
                return AsyncSessionLocal(), True
        else:
            return db, False
    else:
        # 如果没有提供会话，创建一个新的
        return AsyncSessionLocal(), True

@contextlib.contextmanager
def db_operation(db: Union[Session, Iterator[Session], None] = None):
    """数据库操作上下文管理器
    
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