import redis
import aioredis
import json
import logging
import time
from typing import List, Optional, Dict, Any, Set, Tuple, Union
import threading
import os
import asyncio
from datetime import datetime
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis管理器，用于处理Redis连接和操作
    
    该类提供了Redis连接管理、日志存储、任务状态更新和WebSocket连接管理的功能。
    所有方法都是类方法，用于集中管理Redis资源。
    """
    
    # Redis连接实例（单例模式）
    _redis_instance = None
    _async_redis_instance = None
    
    # WebSocket连接注册表 {eval_id: {client_id: pubsub}}
    _websocket_registry = {}
    
    # 活跃的通道追踪 {eval_id: set(client_ids)}
    _active_channels = {}
    
    # 类方法锁，用于线程安全操作
    _lock = threading.Lock()
    
    #------------------
    # 连接管理方法
    #------------------
    
    @classmethod
    def get_instance(cls) -> Optional[redis.Redis]:
        """获取Redis同步连接实例（单例模式）
        
        Returns:
            Optional[redis.Redis]: Redis连接实例，连接失败则返回None
        """
        if cls._redis_instance is None:
            with cls._lock:
                if cls._redis_instance is None:
                    try:
                        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                        cls._redis_instance = redis.Redis.from_url(
                            redis_url, decode_responses=True
                        )
                        logger.info(f"已连接到Redis: {redis_url}")
                    except Exception as e:
                        logger.error(f"Redis连接失败: {str(e)}")
                        cls._redis_instance = None
        return cls._redis_instance
    
    @classmethod
    async def get_async_instance(cls) -> Optional[aioredis.Redis]:
        """获取Redis异步连接实例（单例模式）
        
        Returns:
            Optional[aioredis.Redis]: Redis异步连接实例，连接失败则返回None
        """
        if cls._async_redis_instance is None:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                cls._async_redis_instance = aioredis.from_url(
                    redis_url, decode_responses=True
                )
                logger.info(f"已连接到异步Redis: {redis_url}")
            except Exception as e:
                logger.error(f"异步Redis连接失败: {str(e)}")
                cls._async_redis_instance = None
        return cls._async_redis_instance
    
    #------------------
    # 频道和键名管理
    #------------------
    
    @classmethod
    def get_log_channel(cls, eval_id) -> str:
        """获取日志通道名称
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            str: 日志通道名称
        """
        return f"eval:{eval_id}:logs"
    
    @classmethod
    def get_status_channel(cls, eval_id) -> str:
        """获取状态通道名称
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            str: 状态通道名称
        """
        return f"eval:{eval_id}:status"
    
    @classmethod
    def get_log_key(cls, eval_id) -> str:
        """获取日志存储键名
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            str: 日志存储键名
        """
        return f"eval:{eval_id}:log_data"
    
    @classmethod
    def get_status_key(cls, eval_id) -> str:
        """获取状态存储键名
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            str: 状态存储键名
        """
        return f"eval:{eval_id}:status"
        
    @classmethod
    def get_connection_key(cls, eval_id) -> str:
        """获取连接信息存储键名
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            str: 连接信息存储键名
        """
        return f"eval:{eval_id}:connections"
    
    #------------------
    # WebSocket连接管理
    #------------------
    
    @classmethod
    def register_websocket(cls, task_id: int, client_id: str, websocket: WebSocket) -> None:
        """注册WebSocket连接
        
        Args:
            task_id: 任务ID
            client_id: 客户端ID
            websocket: WebSocket连接对象
        """
        # 初始化任务的WebSocket注册表
        if task_id not in cls._websocket_registry:
            cls._websocket_registry[task_id] = {}
            
        # 添加WebSocket连接
        cls._websocket_registry[task_id][client_id] = websocket
        logger.debug(f"已注册WebSocket连接 - 任务ID: {task_id}, 客户端ID: {client_id}")
        
        # 更新Redis中的连接信息
        try:
            redis_client = cls.get_instance()
            if redis_client:
                connection_key = cls.get_connection_key(task_id)
                redis_client.hset(connection_key, client_id, "active")
        except Exception as e:
            logger.error(f"更新Redis连接信息失败: {str(e)}")

    @classmethod
    async def unregister_websocket(cls, task_id: int, client_id: str) -> None:
        """注销WebSocket连接
        
        Args:
            task_id: 任务ID
            client_id: 客户端ID
        """
        try:
            # 从注册表中移除连接
            if task_id in cls._websocket_registry and client_id in cls._websocket_registry[task_id]:
                # 关闭WebSocket连接
                websocket = cls._websocket_registry[task_id][client_id]
                if not websocket.client_state.value.startswith("DISCONNECTED"):
                    await websocket.close()
                
                # 从注册表中删除
                del cls._websocket_registry[task_id][client_id]
                
                # 如果任务没有更多连接，清理注册表
                if not cls._websocket_registry[task_id]:
                    del cls._websocket_registry[task_id]
                
                logger.debug(f"已注销WebSocket连接 - 任务ID: {task_id}, 客户端ID: {client_id}")
                
                # 更新Redis中的连接信息
                redis_client = cls.get_instance()
                if redis_client:
                    connection_key = cls.get_connection_key(task_id)
                    redis_client.hdel(connection_key, client_id)
                    
        except Exception as e:
            logger.error(f"注销WebSocket连接失败: {str(e)}")
            # 即使出错也尝试清理注册表
            if task_id in cls._websocket_registry and client_id in cls._websocket_registry[task_id]:
                del cls._websocket_registry[task_id][client_id]
    
    @classmethod
    async def subscribe_to_logs(cls, eval_id, client_id) -> Optional[aioredis.client.PubSub]:
        """订阅日志通道
        
        创建PubSub订阅并注册到WebSocket连接
        
        Args:
            eval_id: 评估任务ID
            client_id: 客户端唯一标识
            
        Returns:
            Optional[aioredis.client.PubSub]: Redis PubSub对象，失败则返回None
        """
        try:
            redis = await cls.get_async_instance()
            if not redis:
                logger.error("无法获取Redis连接")
                return None
            
            channel = cls.get_log_channel(eval_id)
            
            # 创建PubSub对象
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel)
            
            # 注册WebSocket连接
            cls.register_websocket(eval_id, client_id, pubsub)
            
            logger.debug(f"已订阅日志通道: {channel}, 客户端={client_id}")
            return pubsub
        except Exception as e:
            logger.error(f"订阅日志通道出错: {str(e)}")
            return None
    
    #------------------
    # 日志管理
    #------------------
    
    @classmethod
    def append_log(cls, eval_id, log_line, max_recent_logs=5) -> bool:
        """添加单条日志到Redis并发布到通道
        
        Args:
            eval_id: 评估任务ID
            log_line: 日志行
            max_recent_logs: 检查最近日志的数量，用于去重
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not log_line or not log_line.strip():
                return False
                
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return False
            
            log_key = cls.get_log_key(eval_id)
            channel = cls.get_log_channel(eval_id)
            
            # 检查是否为重复日志
            is_duplicate = False
            
            # 获取最近的日志进行去重
            recent_logs = redis_client.lrange(log_key, -max_recent_logs, -1)
            for recent_log in recent_logs:
                try:
                    # 解析为JSON，比较log字段
                    log_data = json.loads(recent_log)
                    if log_data.get("log") == log_line:
                        is_duplicate = True
                        break
                except json.JSONDecodeError:
                    # 旧格式，直接比较
                    if recent_log == log_line:
                        is_duplicate = True
                        break
            
            # 如果不是重复日志，则添加并发布
            if not is_duplicate:
                # 创建包含时间戳的日志对象
                log_data = json.dumps({
                    "log": log_line,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 添加到列表
                redis_client.rpush(log_key, log_data)
                
                # 发布到通道
                redis_client.publish(channel, log_data)
                return True
            
            return False
        except Exception as e:
            logger.error(f"添加日志到Redis出错: {str(e)}")
            return False
    
    @classmethod
    def batch_append_logs(cls, eval_id, log_lines, max_recent_logs=10) -> int:
        """批量添加日志到Redis并发布到通道
        
        高效地批量处理多条日志，避免重复和多次连接
        
        Args:
            eval_id: 评估任务ID
            log_lines: 日志行列表
            max_recent_logs: 检查最近日志的数量，用于去重
            
        Returns:
            int: 成功添加的日志数量
        """
        if not log_lines:
            return 0
            
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return 0
            
            log_key = cls.get_log_key(eval_id)
            channel = cls.get_log_channel(eval_id)
            
            # 获取最近的日志进行去重
            recent_logs = redis_client.lrange(log_key, -max_recent_logs, -1)
            
            # 创建已存在日志的集合用于去重
            recent_log_set = set()
            for log_entry in recent_logs:
                try:
                    # 尝试解析JSON
                    log_data = json.loads(log_entry)
                    recent_log_set.add(log_data.get("log", ""))
                except json.JSONDecodeError:
                    # 旧格式，直接添加
                    recent_log_set.add(log_entry)
            
            # 过滤掉空行和重复行
            unique_logs = []
            for log_line in log_lines:
                if log_line and log_line.strip() and log_line not in recent_log_set:
                    # 创建包含时间戳的日志对象
                    log_data = json.dumps({
                        "log": log_line,
                        "timestamp": datetime.now().isoformat()
                    })
                    unique_logs.append(log_data)
                    recent_log_set.add(log_line)  # 防止批量中的重复
            
            if not unique_logs:
                return 0
                
            # 使用管道批量操作，提高效率
            with redis_client.pipeline() as pipe:
                # 添加到列表
                pipe.rpush(log_key, *unique_logs)
                
                # 发布到通道
                for log_data in unique_logs:
                    pipe.publish(channel, log_data)
                
                pipe.execute()
            
            return len(unique_logs)
        except Exception as e:
            logger.error(f"批量添加日志到Redis出错: {str(e)}")
            return 0
    
    @classmethod
    def get_logs(cls, eval_id, max_lines=None) -> List[str]:
        """获取任务的日志
        
        Args:
            eval_id: 评估任务ID
            max_lines: 最大返回行数，None表示返回全部
            
        Returns:
            List[str]: 日志行列表
        """
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return []
            
            log_key = cls.get_log_key(eval_id)
            
            # 获取所有日志或有限数量的日志
            if max_lines is not None:
                logs = redis_client.lrange(log_key, -max_lines, -1)
            else:
                logs = redis_client.lrange(log_key, 0, -1)
            
            # 解析JSON格式的日志
            parsed_logs = []
            for log_entry in logs:
                try:
                    # 尝试解析JSON格式
                    log_data = json.loads(log_entry)
                    parsed_logs.append(log_data.get("log", log_entry))
                except json.JSONDecodeError:
                    # 兼容旧格式：直接添加文本
                    parsed_logs.append(log_entry)
            
            return parsed_logs
        except Exception as e:
            logger.error(f"获取Redis日志出错: {str(e)}")
            return []
    
    @classmethod
    def clear_logs(cls, eval_id) -> bool:
        """清除任务的所有日志
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return False
            
            log_key = cls.get_log_key(eval_id)
            redis_client.delete(log_key)
            
            # 发布清除日志的消息
            channel = cls.get_log_channel(eval_id)
            clear_message = json.dumps({
                "action": "clear_logs",
                "timestamp": datetime.now().isoformat()
            })
            redis_client.publish(channel, clear_message)
            
            return True
        except Exception as e:
            logger.error(f"清除Redis日志出错: {str(e)}")
            return False
    
    @classmethod
    def publish_log(cls, eval_id: int, log_data: Union[str, Dict[str, Any]]) -> bool:
        """发布日志到指定的通道
        
        Args:
            eval_id: 评估任务ID
            log_data: 日志数据，可以是JSON字符串或字典对象
            
        Returns:
            bool: 发布是否成功
        """
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return False
            
            channel = cls.get_log_channel(eval_id)
            
            # 如果提供的是字典，转换为JSON字符串
            log_data_str = log_data if isinstance(log_data, str) else json.dumps(log_data)
            
            # 发布到通道
            redis_client.publish(channel, log_data_str)
            return True
        except Exception as e:
            logger.error(f"发布日志到Redis通道出错: {str(e)}")
            return False
    
    #------------------
    # 任务状态管理
    #------------------
    
    @classmethod
    def update_task_status(cls, eval_id, status) -> bool:
        """更新任务状态并发布到通道
        
        Args:
            eval_id: 评估任务ID
            status: 任务状态
            
        Returns:
            bool: 操作是否成功
        """
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return False
            
            status_key = cls.get_status_key(eval_id)
            channel = cls.get_status_channel(eval_id)
            
            # 确保状态包含时间戳
            if isinstance(status, dict) and "timestamp" not in status:
                status["timestamp"] = datetime.now().isoformat()
            
            status_json = json.dumps(status)
            
            # 更新状态
            redis_client.set(status_key, status_json)
            
            # 发布到通道
            redis_client.publish(channel, status_json)
            
            return True
        except Exception as e:
            logger.error(f"更新任务状态出错: {str(e)}")
            return False
    
    @classmethod
    def get_task_status(cls, task_id: int) -> Optional[Dict[str, Any]]:
        """从Redis获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态，不存在则返回None
        """
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return None
                
            status_json = redis_client.get(cls.get_status_key(task_id))
            if status_json:
                return json.loads(status_json)
            return None
        except Exception as e:
            logger.error(f"从Redis获取任务状态失败: {str(e)}")
            return None
    
    @classmethod
    def set_task_status(cls, task_id: int, status: Dict[str, Any]) -> None:
        """直接设置任务状态，带过期时间
        
        Args:
            task_id: 任务ID
            status: 任务状态
        """
        try:
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接")
                return
                
            # 添加时间戳
            if "timestamp" not in status:
                status["timestamp"] = datetime.now().isoformat()
                
            redis_client.set(
                cls.get_status_key(task_id), 
                json.dumps(status),
                ex=86400  # 1天过期
            )
        except Exception as e:
            logger.error(f"设置Redis任务状态失败: {str(e)}")
    
    #------------------
    # 资源清理
    #------------------
    
    @classmethod
    async def delete_task_data(cls, task_id: int) -> None:
        """删除任务相关的所有Redis数据
        
        包括日志、状态和连接信息的清理，同时关闭相关的WebSocket连接
        
        Args:
            task_id: 任务ID
        """
        try:
            # 获取Redis连接
            redis_client = cls.get_instance()
            if not redis_client:
                logger.error("无法获取Redis连接清理任务数据")
                return
                
            # 删除Redis中的数据
            redis_client.delete(cls.get_log_key(task_id))
            redis_client.delete(cls.get_status_key(task_id))
            redis_client.delete(cls.get_connection_key(task_id))
            
            # 记录删除操作
            logger.info(f"已删除任务 {task_id} 的Redis数据")
            
            # 清理WebSocket连接
            # 获取所有相关的客户端ID
            if task_id in cls._websocket_registry:
                client_ids = list(cls._websocket_registry[task_id].keys())
                
                # 逐个注销WebSocket连接
                for client_id in client_ids:
                    await cls.unregister_websocket(task_id, client_id)
            
            # 清理活跃通道记录
            if task_id in cls._active_channels:
                del cls._active_channels[task_id]
                    
        except Exception as e:
            logger.error(f"删除任务Redis数据失败: {str(e)}") 