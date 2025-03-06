"""资源管理器测试模块

测试ResourceManager类和相关功能
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from apps.server.src.utils.resource_manager import ResourceManager


@pytest.mark.asyncio
class TestResourceManager:
    """测试ResourceManager类"""
    
    async def test_close_websocket(self):
        """测试安全关闭WebSocket连接"""
        # 创建模拟WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.close = AsyncMock()
        
        # 调用close_websocket
        result = await ResourceManager.close_websocket(mock_websocket, code=1001, reason="测试关闭")
        
        # 验证结果
        assert result is True
        mock_websocket.close.assert_called_once_with(code=1001, reason="测试关闭")
    
    async def test_close_websocket_already_closed(self):
        """测试关闭已关闭的WebSocket连接"""
        # 创建模拟WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.DISCONNECTED
        mock_websocket.close = AsyncMock()
        
        # 调用close_websocket
        result = await ResourceManager.close_websocket(mock_websocket)
        
        # 验证结果
        assert result is False
        mock_websocket.close.assert_not_called()
    
    async def test_close_websocket_with_exception(self):
        """测试关闭WebSocket连接时发生异常"""
        # 创建模拟WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.close = AsyncMock(side_effect=Exception("测试异常"))
        
        # 调用close_websocket
        result = await ResourceManager.close_websocket(mock_websocket)
        
        # 验证结果
        assert result is False
        mock_websocket.close.assert_called_once()
    
    async def test_cleanup_pubsub(self):
        """测试清理PubSub资源"""
        # 创建模拟PubSub
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = MagicMock()
        mock_pubsub.close = MagicMock()
        
        # 调用cleanup_pubsub
        result = await ResourceManager.cleanup_pubsub(mock_pubsub)
        
        # 验证结果
        assert result is True
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()
    
    async def test_cleanup_pubsub_with_exceptions(self):
        """测试清理PubSub资源时发生异常"""
        # 创建模拟PubSub
        mock_pubsub = MagicMock()
        mock_pubsub.unsubscribe = MagicMock(side_effect=Exception("取消订阅异常"))
        mock_pubsub.close = MagicMock(side_effect=Exception("关闭异常"))
        
        # 调用cleanup_pubsub
        result = await ResourceManager.cleanup_pubsub(mock_pubsub)
        
        # 验证结果
        assert result is True  # 即使出现异常，也应该返回True表示尝试了清理
        mock_pubsub.unsubscribe.assert_called_once()
        mock_pubsub.close.assert_called_once()
    
    async def test_websocket_context(self):
        """测试WebSocket上下文管理器"""
        # 创建模拟WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.close = AsyncMock()
        
        # 使用上下文管理器
        async with ResourceManager.websocket_context(mock_websocket, eval_id=123) as ws:
            assert ws is mock_websocket
            # 在上下文内执行操作
            await ws.send_text("测试消息")
        
        # 验证close被调用
        mock_websocket.close.assert_called_once()
    
    async def test_websocket_context_with_exception(self):
        """测试WebSocket上下文管理器异常处理"""
        # 创建模拟WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        mock_websocket.close = AsyncMock()
        
        # 使用上下文管理器，内部抛出异常
        with pytest.raises(ValueError):
            async with ResourceManager.websocket_context(mock_websocket) as ws:
                raise ValueError("测试异常")
        
        # 验证关闭被调用
        mock_websocket.close.assert_called_once()
    
    async def test_pubsub_context(self):
        """测试PubSub上下文管理器"""
        # 创建模拟对象
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        # 替换RedisManager.get_instance
        with patch('apps.server.src.utils.resource_manager.RedisManager.get_instance', return_value=mock_redis):
            # 使用上下文管理器
            async with ResourceManager.pubsub_context("test:channel") as pubsub:
                assert pubsub is mock_pubsub
                # 验证订阅被调用
                mock_pubsub.subscribe.assert_called_once_with("test:channel")
        
        # 验证清理函数被调用
        with patch('apps.server.src.utils.resource_manager.ResourceManager.cleanup_pubsub', new_callable=AsyncMock) as mock_cleanup:
            # 使用上下文管理器
            with patch('apps.server.src.utils.resource_manager.RedisManager.get_instance', return_value=mock_redis):
                async with ResourceManager.pubsub_context("test:channel"):
                    pass
            
            # 验证清理函数被调用
            mock_cleanup.assert_called_once()
    
    async def test_websocket_pubsub_context(self):
        """测试WebSocket和PubSub组合上下文管理器"""
        # 创建模拟对象
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        
        mock_websocket = AsyncMock()
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # 替换方法
        with patch('apps.server.src.utils.resource_manager.RedisManager.get_instance', return_value=mock_redis):
            with patch('apps.server.src.utils.resource_manager.ResourceManager.cleanup_pubsub', new_callable=AsyncMock) as mock_cleanup_pubsub:
                with patch('apps.server.src.utils.resource_manager.ResourceManager.close_websocket', new_callable=AsyncMock) as mock_close_websocket:
                    # 使用上下文管理器
                    async with ResourceManager.websocket_pubsub_context(mock_websocket, "test:channel", eval_id=456) as pubsub:
                        assert pubsub is mock_pubsub
                        # 验证订阅被调用
                        mock_pubsub.subscribe.assert_called_once_with("test:channel")
                    
                    # 验证清理函数被调用
                    mock_cleanup_pubsub.assert_called_once_with(mock_pubsub)
                    mock_close_websocket.assert_called_once_with(mock_websocket)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 