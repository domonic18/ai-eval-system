"""数据库会话管理器测试模块

测试DatabaseSessionManager类和相关辅助函数
"""

import unittest
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

from apps.server.src.utils.db_utils import (
    DatabaseSessionManager,
    get_db_session,
    async_db_operation
)
from apps.server.src.models.eval import Evaluation


class TestDatabaseSessionManager(unittest.TestCase):
    """测试DatabaseSessionManager类"""
    
    def test_session_context_manager(self):
        """测试同步会话上下文管理器"""
        # 使用上下文管理器获取会话
        with DatabaseSessionManager.session() as db:
            # 验证是否获取到Session实例
            self.assertIsInstance(db, Session)
            
            # 模拟查询操作
            result = db.query(Evaluation).limit(1).all()
            # 仅验证操作不抛出异常
    
    def test_session_context_manager_with_exception(self):
        """测试同步会话上下文管理器异常处理"""
        # 创建模拟会话和回滚方法
        mock_session = MagicMock()
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()
        
        # 替换SessionLocal
        with patch('apps.server.src.utils.db_utils.SessionLocal', return_value=mock_session):
            try:
                with DatabaseSessionManager.session() as db:
                    # 抛出异常模拟数据库操作错误
                    raise ValueError("测试异常")
            except ValueError:
                # 验证回滚是否被调用
                mock_session.rollback.assert_called_once()
            finally:
                # 验证关闭是否被调用
                mock_session.close.assert_called_once()
    
    def test_execute_with_session(self):
        """测试使用会话执行函数"""
        # 执行简单查询
        result = DatabaseSessionManager.execute_with_session(
            lambda db: db.query(Evaluation).limit(5).all()
        )
        # 验证结果是列表
        self.assertIsInstance(result, list)


@pytest.mark.asyncio
class TestAsyncDatabaseOperations:
    """测试异步数据库操作"""
    
    async def test_async_session(self):
        """测试异步会话上下文管理器"""
        async with DatabaseSessionManager.async_session() as db:
            # 验证是否获取到Session实例
            assert isinstance(db, Session)
            
            # 模拟查询操作，使用to_thread执行同步操作
            result = await asyncio.to_thread(lambda: db.query(Evaluation).limit(1).all())
            # 仅验证操作不抛出异常
    
    async def test_execute_with_async_session(self):
        """测试使用异步会话执行函数"""
        # 执行简单查询
        result = await DatabaseSessionManager.execute_with_async_session(
            lambda db: db.query(Evaluation).limit(5).all()
        )
        # 验证结果是列表
        assert isinstance(result, list)
    
    async def test_async_db_operation(self):
        """测试异步数据库操作上下文管理器"""
        # 测试自动创建会话
        async with async_db_operation() as db:
            assert isinstance(db, Session)
            # 执行简单查询
            result = await asyncio.to_thread(lambda: db.query(Evaluation).limit(1).all())
            # 仅验证操作不抛出异常
        
        # 测试传入现有会话
        existing_db = MagicMock()
        async with async_db_operation(existing_db) as db:
            assert db is existing_db


@pytest.mark.asyncio
class TestCompatibilityFunctions:
    """测试兼容性函数"""
    
    async def test_get_db_session(self):
        """测试get_db_session兼容函数"""
        with get_db_session() as db:
            # 验证是否获取到Session实例
            assert isinstance(db, Session)
            
            # 执行简单查询
            db.query(Evaluation).limit(1).all()
            # 仅验证操作不抛出异常


if __name__ == "__main__":
    unittest.main() 