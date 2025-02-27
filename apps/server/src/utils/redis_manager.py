import redis
import aioredis
import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class RedisManager:
    _instance = None
    _async_instance = None
    
    @classmethod
    def get_instance(cls):
        """获取Redis同步客户端单例"""
        if cls._instance is None:
            cls._instance = redis.Redis(
                host='localhost',  # 应该从配置中读取
                port=6379,
                db=0,
                decode_responses=True
            )
        return cls._instance
    
    @classmethod
    async def get_async_instance(cls):
        """获取Redis异步客户端单例"""
        if cls._async_instance is None:
            cls._async_instance = await aioredis.from_url(
                "redis://localhost:6379", 
                decode_responses=True
            )
        return cls._async_instance
    
    @classmethod
    def get_log_key(cls, task_id: int) -> str:
        """获取存储日志的Redis键名"""
        return f"task:{task_id}:logs"
    
    @classmethod
    def get_log_channel(cls, task_id: int) -> str:
        """获取发布日志更新的Redis频道名"""
        return f"task:{task_id}:logs:channel"
    
    @classmethod
    def get_status_key(cls, task_id: int) -> str:
        """获取存储任务状态的Redis键名"""
        return f"task:{task_id}:status"
    
    @classmethod
    def append_log(cls, task_id: int, log_line: str) -> None:
        """添加日志行到Redis并发布更新"""
        try:
            redis_client = cls.get_instance()
            # 将日志行添加到列表中
            redis_client.rpush(cls.get_log_key(task_id), log_line)
            # 设置TTL (1天)
            redis_client.expire(cls.get_log_key(task_id), 86400)
            # 发布日志更新
            redis_client.publish(cls.get_log_channel(task_id), log_line)
        except Exception as e:
            logger.error(f"向Redis添加日志失败: {str(e)}")
    
    @classmethod
    def get_logs(cls, task_id: int, max_lines: int = 100) -> List[str]:
        """获取指定任务的最新日志"""
        try:
            redis_client = cls.get_instance()
            # 获取列表长度
            log_length = redis_client.llen(cls.get_log_key(task_id))
            # 如果请求的行数超过实际行数，则获取全部
            start_index = max(0, log_length - max_lines)
            # 获取日志
            logs = redis_client.lrange(cls.get_log_key(task_id), start_index, -1)
            return logs
        except Exception as e:
            logger.error(f"从Redis获取日志失败: {str(e)}")
            return []
    
    @classmethod
    def update_task_status(cls, task_id: int, status: Dict[str, Any]) -> None:
        """更新任务状态到Redis"""
        try:
            redis_client = cls.get_instance()
            redis_client.set(
                cls.get_status_key(task_id), 
                json.dumps(status),
                ex=86400  # 1天过期
            )
        except Exception as e:
            logger.error(f"更新Redis任务状态失败: {str(e)}")
    
    @classmethod
    def get_task_status(cls, task_id: int) -> Optional[Dict[str, Any]]:
        """从Redis获取任务状态"""
        try:
            redis_client = cls.get_instance()
            status_json = redis_client.get(cls.get_status_key(task_id))
            if status_json:
                return json.loads(status_json)
            return None
        except Exception as e:
            logger.error(f"从Redis获取任务状态失败: {str(e)}")
            return None 