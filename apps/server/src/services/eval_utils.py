"""评估服务工具模块

提供评估服务使用的资源管理和数据库会话管理辅助函数
"""

import logging
import json
import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import WebSocket
from fastapi.websockets import WebSocketState
from redis.client import PubSub

from apps.server.src.models.eval import Evaluation
from apps.server.src.utils.redis_manager import RedisManager
from apps.server.src.utils.db_utils import DatabaseSessionManager, get_db_session

logger = logging.getLogger(__name__)


async def get_and_validate_evaluation(eval_id: int) -> Optional[Evaluation]:
    """获取并验证评估任务是否存在
    
    Args:
        eval_id: 评估ID
        
    Returns:
        Optional[Evaluation]: 评估任务对象，如果不存在则返回None
    """
    try:
        with get_db_session() as db:
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            return evaluation
    except Exception as e:
        logger.error(f"获取评估任务出错 [eval_id={eval_id}]: {str(e)}")
        return None


async def close_websocket(websocket: WebSocket, code: int = 1000, reason: str = "正常关闭") -> bool:
    """安全关闭WebSocket连接
    
    Args:
        websocket: WebSocket连接
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


async def cleanup_pubsub(pubsub: Optional[PubSub] = None) -> bool:
    """清理PubSub资源
    
    Args:
        pubsub: PubSub对象
        
    Returns:
        bool: 是否成功清理
    """
    if not pubsub:
        return False
        
    try:
        pubsub.unsubscribe()
        pubsub.close()
        return True
    except Exception as e:
        logger.warning(f"清理PubSub资源出错: {str(e)}")
        return False


@asynccontextmanager
async def websocket_context(websocket: WebSocket, eval_id: Optional[int] = None) -> AsyncGenerator[WebSocket, None]:
    """WebSocket上下文管理器
    
    用法:
        async with websocket_context(websocket, eval_id) as ws:
            # 使用ws进行WebSocket操作
    """
    try:
        yield websocket
    except Exception as e:
        logger.error(f"WebSocket操作异常 [eval_id={eval_id}]: {str(e)}")
        raise
    finally:
        await close_websocket(websocket)


@asynccontextmanager
async def pubsub_context(channel: str) -> AsyncGenerator[PubSub, None]:
    """PubSub上下文管理器
    
    用法:
        async with pubsub_context("channel:name") as pubsub:
            # 使用pubsub进行订阅操作
    """
    redis = RedisManager.get_instance()
    if not redis:
        raise ValueError("无法获取Redis连接")
        
    pubsub = redis.pubsub()
    
    try:
        pubsub.subscribe(channel)
        yield pubsub
    except Exception as e:
        logger.error(f"PubSub操作异常 [channel={channel}]: {str(e)}")
        raise
    finally:
        await cleanup_pubsub(pubsub) 