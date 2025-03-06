"""任务状态模块

定义任务状态枚举和状态转换函数，用于tasks包中不同模块共享状态定义，
避免循环导入问题
"""

import logging
from enum import Enum, auto
from typing import Optional, Dict, Any
from celery.result import AsyncResult

from apps.server.src.models.eval import EvaluationStatus
from apps.server.src.celery_app import celery_app

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举
    
    定义任务在TaskManager中的不同状态
    """
    PENDING = 1      # 等待中（新创建）
    WAITING = 2      # 等待队列中
    QUEUED = 3       # 已加入Celery队列
    RUNNING = 4      # 正在运行
    COMPLETED = 5    # 已完成
    FAILED = 6       # 失败
    TERMINATED = 7   # 被终止
    
    @staticmethod
    def from_evaluation_status(status: EvaluationStatus) -> 'TaskStatus':
        """从EvaluationStatus转换为TaskStatus"""
        status_map = {
            EvaluationStatus.PENDING: TaskStatus.PENDING,
            EvaluationStatus.RUNNING: TaskStatus.RUNNING,
            EvaluationStatus.COMPLETED: TaskStatus.COMPLETED,
            EvaluationStatus.FAILED: TaskStatus.FAILED,
            EvaluationStatus.TERMINATED: TaskStatus.TERMINATED
        }
        return status_map.get(status, TaskStatus.PENDING)
    
    def to_evaluation_status(self) -> EvaluationStatus:
        """将TaskStatus转换为EvaluationStatus"""
        status_map = {
            TaskStatus.PENDING: EvaluationStatus.PENDING,  
            TaskStatus.WAITING: EvaluationStatus.PENDING,  # 等待中的任务在数据库中为PENDING
            TaskStatus.QUEUED: EvaluationStatus.PENDING,   # 队列中的任务在数据库中仍为PENDING
            TaskStatus.RUNNING: EvaluationStatus.RUNNING,
            TaskStatus.COMPLETED: EvaluationStatus.COMPLETED,
            TaskStatus.FAILED: EvaluationStatus.FAILED,
            TaskStatus.TERMINATED: EvaluationStatus.TERMINATED
        }
        return status_map.get(self, EvaluationStatus.PENDING)


def format_task_status(status: TaskStatus, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """格式化任务状态
    
    Args:
        status: 任务状态
        metadata: 附加元数据
        
    Returns:
        Dict[str, Any]: 格式化后的状态数据
    """
    result = {
        "status": status.name,
        "db_status": status.to_evaluation_status().value
    }
    
    if metadata:
        result.update(metadata)
    
    return result


def get_celery_task_state(task_id: str) -> Optional[str]:
    """获取Celery任务状态
    
    Args:
        task_id: Celery任务ID
        
    Returns:
        Optional[str]: Celery任务状态，如果任务不存在则返回None
    """
    try:
        task = AsyncResult(task_id, app=celery_app)
        return task.state
    except Exception as e:
        logger.warning(f"获取Celery任务状态失败 [task_id={task_id}]: {str(e)}")
        return None


def map_celery_state_to_task_status(state: str) -> TaskStatus:
    """将Celery任务状态映射为TaskStatus
    
    Args:
        state: Celery任务状态字符串
        
    Returns:
        TaskStatus: 映射后的任务状态
    """
    # Celery状态详见: https://docs.celeryq.dev/en/stable/reference/celery.result.html#celery.result.AsyncResult.state
    state_map = {
        'PENDING': TaskStatus.PENDING,       # 任务等待中
        'STARTED': TaskStatus.RUNNING,       # 任务已开始执行
        'RETRY': TaskStatus.RUNNING,         # 任务正在重试
        'SUCCESS': TaskStatus.COMPLETED,     # 任务成功完成
        'FAILURE': TaskStatus.FAILED,        # 任务执行失败
        'REVOKED': TaskStatus.TERMINATED,    # 任务被撤销
    }
    return state_map.get(state, TaskStatus.PENDING)


def safe_parse_task_status(status_value) -> TaskStatus:
    """安全解析任务状态值
    
    从多种不同类型的输入安全地解析为TaskStatus枚举
    
    Args:
        status_value: 状态值，可能是整数、字符串、字节串或TaskStatus实例
        
    Returns:
        TaskStatus: 解析后的任务状态，如果无法解析则返回PENDING
        
    Examples:
        >>> safe_parse_task_status(4)
        TaskStatus.RUNNING
        >>> safe_parse_task_status("4")
        TaskStatus.RUNNING
        >>> safe_parse_task_status(b"4")
        TaskStatus.RUNNING
        >>> safe_parse_task_status("RUNNING")
        TaskStatus.RUNNING
    """
    # 如果已经是TaskStatus实例，直接返回
    if isinstance(status_value, TaskStatus):
        return status_value
        
    # 处理字节串
    if isinstance(status_value, bytes):
        try:
            status_value = status_value.decode('utf-8')
        except:
            return TaskStatus.PENDING
    
    # 处理名称字符串 (如 "RUNNING")
    if isinstance(status_value, str):
        # 先检查是否是枚举名称
        try:
            upper_value = status_value.upper()
            for status in TaskStatus:
                if status.name == upper_value:
                    return status
            
            # 尝试转换为整数
            status_value = int(status_value)
        except (ValueError, TypeError):
            # 如果无法转换为整数，返回默认状态
            return TaskStatus.PENDING
    
    # 处理整数值
    try:
        # 注意：这里使用枚举值匹配而不是直接用整数构造枚举
        for status in TaskStatus:
            if status.value == status_value:
                return status
        
        # 如果找不到匹配的值，返回默认状态
        return TaskStatus.PENDING
    except Exception:
        # 处理任何其他异常
        return TaskStatus.PENDING 