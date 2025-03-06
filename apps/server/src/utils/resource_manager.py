"""资源管理工具模块

提供资源管理和清理功能，确保资源在异常情况下也能正确释放
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Callable, List, Union, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from redis.client import PubSub

from apps.server.src.utils.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class ResourceManager:
    """资源管理类
    
    提供各种资源的管理和清理功能，确保资源在异常情况下也能正确释放
    """
    
    @staticmethod
    async def close_websocket(websocket: WebSocket, code: int = 1000, reason: str = "正常关闭") -> bool:
        """安全关闭WebSocket连接
        
        Args:
            websocket: 要关闭的WebSocket连接
            code: 关闭代码
            reason: 关闭原因
            
        Returns:
            bool: 是否成功关闭
        """
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=code, reason=reason)
                return True
            return False
        except Exception as e:
            logger.warning(f"关闭WebSocket连接出错: {str(e)}")
            return False
    
    @staticmethod
    async def cleanup_pubsub(pubsub: PubSub) -> bool:
        """清理Redis PubSub资源
        
        Args:
            pubsub: 要清理的PubSub对象
            
        Returns:
            bool: 是否成功清理
        """
        try:
            if pubsub:
                # 首先尝试取消所有订阅
                try:
                    pubsub.unsubscribe()
                except Exception as e:
                    logger.warning(f"取消PubSub订阅出错: {str(e)}")
                
                # 然后关闭连接
                try:
                    pubsub.close()
                except Exception as e:
                    logger.warning(f"关闭PubSub连接出错: {str(e)}")
                
                return True
            return False
        except Exception as e:
            logger.warning(f"清理PubSub资源出错: {str(e)}")
            return False
    
    @staticmethod
    @asynccontextmanager
    async def websocket_context(websocket: WebSocket, eval_id: Optional[int] = None) -> AsyncGenerator[WebSocket, None]:
        """WebSocket连接上下文管理器
        
        用法:
            async with ResourceManager.websocket_context(websocket) as ws:
                # 使用ws进行WebSocket操作
                
        确保在退出上下文时自动关闭WebSocket连接
        
        Args:
            websocket: WebSocket连接
            eval_id: 可选的评估ID，用于日志记录
            
        Yields:
            WebSocket: WebSocket连接对象
        """
        id_log = f" [eval_id={eval_id}]" if eval_id is not None else ""
        try:
            yield websocket
        except Exception as e:
            logger.error(f"WebSocket操作异常{id_log}: {str(e)}")
            raise
        finally:
            await ResourceManager.close_websocket(websocket)
            logger.info(f"WebSocket连接已关闭{id_log}")
    
    @staticmethod
    @asynccontextmanager
    async def pubsub_context(channel: str) -> AsyncGenerator[PubSub, None]:
        """Redis PubSub上下文管理器
        
        用法:
            async with ResourceManager.pubsub_context("channel:name") as pubsub:
                # 使用pubsub进行订阅和监听操作
                
        确保在退出上下文时自动清理PubSub资源
        
        Args:
            channel: 要订阅的频道名称
            
        Yields:
            PubSub: Redis PubSub对象
        """
        # 获取Redis连接
        redis = RedisManager.get_instance()
        if not redis:
            raise ValueError("无法获取Redis连接")
        
        # 创建PubSub对象
        pubsub = redis.pubsub()
        
        try:
            # 订阅频道
            pubsub.subscribe(channel)
            yield pubsub
        except Exception as e:
            logger.error(f"PubSub操作异常 [channel={channel}]: {str(e)}")
            raise
        finally:
            # 清理资源
            await ResourceManager.cleanup_pubsub(pubsub)
            logger.info(f"PubSub资源已清理 [channel={channel}]")
    
    @staticmethod
    @asynccontextmanager
    async def websocket_pubsub_context(websocket: WebSocket, channel: str, eval_id: Optional[int] = None) -> AsyncGenerator[PubSub, None]:
        """WebSocket和PubSub的组合上下文管理器
        
        用法:
            async with ResourceManager.websocket_pubsub_context(websocket, "channel:name") as pubsub:
                # 使用websocket和pubsub进行操作
                
        确保在退出上下文时自动清理WebSocket和PubSub资源
        
        Args:
            websocket: WebSocket连接
            channel: 要订阅的频道名称
            eval_id: 可选的评估ID，用于日志记录
            
        Yields:
            PubSub: Redis PubSub对象
        """
        id_log = f" [eval_id={eval_id}]" if eval_id is not None else ""
        
        # 获取Redis连接
        redis = RedisManager.get_instance()
        if not redis:
            raise ValueError("无法获取Redis连接")
        
        # 创建PubSub对象
        pubsub = redis.pubsub()
        
        try:
            # 订阅频道
            pubsub.subscribe(channel)
            yield pubsub
        except Exception as e:
            logger.error(f"WebSocket/PubSub操作异常{id_log} [channel={channel}]: {str(e)}")
            raise
        finally:
            # 清理资源
            await ResourceManager.cleanup_pubsub(pubsub)
            await ResourceManager.close_websocket(websocket)
            logger.info(f"WebSocket和PubSub资源已清理{id_log} [channel={channel}]") 