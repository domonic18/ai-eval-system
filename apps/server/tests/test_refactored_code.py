"""集成测试模块

测试重构后的代码是否正常工作，包括数据库会话管理、任务状态管理和资源清理
"""

import unittest
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.utils.db_utils import DatabaseSessionManager
from apps.server.src.services.eval_utils import (
    get_and_validate_evaluation,
    close_websocket,
    cleanup_pubsub,
    websocket_context,
    pubsub_context
)
from apps.server.src.tasks.task_status import TaskStatus


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_database_session_with_task_status(self):
        """测试数据库会话管理器与任务状态枚举的集成"""
        # 测试数据库会话与任务状态转换
        with DatabaseSessionManager.session() as db:
            # 尝试查询一个评估任务
            evaluation = db.query(Evaluation).filter(Evaluation.status == EvaluationStatus.PENDING.value).first()
            if evaluation:
                # 测试状态转换
                task_status = TaskStatus.from_evaluation_status(EvaluationStatus(evaluation.status))
                db_status = task_status.to_evaluation_status()
                self.assertEqual(db_status, EvaluationStatus.PENDING)


@pytest.mark.asyncio
class TestAsyncIntegration:
    """异步集成测试"""
    
    async def test_websocket_resource_management(self):
        """测试WebSocket资源管理"""
        # 创建模拟WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.close = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # 使用WebSocket上下文管理器
        async with websocket_context(mock_websocket, eval_id=123) as ws:
            # 发送测试消息
            await ws.send_text(json.dumps({"event": "test", "data": "message"}))
            mock_websocket.send_text.assert_called_once()
        
        # 验证WebSocket被关闭
        mock_websocket.close.assert_called_once()
    
    async def test_pubsub_resource_management(self):
        """测试PubSub资源管理"""
        # 创建模拟对象
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        # 创建mock的Redis连接
        with patch('apps.server.src.services.eval_utils.RedisManager.get_instance', return_value=mock_redis):
            # 与mock的cleanup_pubsub
            with patch('apps.server.src.services.eval_utils.cleanup_pubsub', new_callable=AsyncMock) as mock_cleanup:
                # 使用PubSub上下文管理器
                async with pubsub_context("test:channel") as pubsub:
                    # 验证PubSub是否正确订阅
                    mock_pubsub.subscribe.assert_called_once_with("test:channel")
                
                # 验证清理函数是否被调用
                mock_cleanup.assert_called_once_with(mock_pubsub)


if __name__ == "__main__":
    unittest.main() 