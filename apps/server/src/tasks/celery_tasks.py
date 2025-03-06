"""Celery任务实现

包含所有Celery异步任务的定义和实现
"""

import logging
import traceback
import json
from typing import Optional, Dict, Any
from datetime import datetime

from celery import shared_task

from apps.server.src.celery_app import celery_app
from apps.server.src.models.eval import Evaluation
# 使用共享的任务状态模块
from apps.server.src.tasks.task_status import TaskStatus
from apps.server.src.utils.db_utils import DatabaseSessionManager
from apps.server.src.utils.redis_manager import RedisManager

# 配置日志
logger = logging.getLogger(__name__)

# Redis任务状态键名和通道名
def get_task_status_key(eval_id: int) -> str:
    return f"task:{eval_id}:status"

def get_task_message_key(eval_id: int) -> str:
    return f"task:{eval_id}:message"

def get_task_result_key(eval_id: int) -> str:
    return f"task:{eval_id}:result"

def get_task_channel(eval_id: int) -> str:
    return f"task:{eval_id}:update"

def publish_task_status(eval_id: int, status: TaskStatus, message: str = None, result: Any = None) -> bool:
    """发布任务状态到Redis
    
    Args:
        eval_id: 评估ID
        status: 任务状态
        message: 状态消息
        result: 任务结果数据
        
    Returns:
        bool: 是否成功发布
    """
    redis_client = RedisManager.get_instance()
    if not redis_client:
        logger.error(f"无法获取Redis客户端，无法发布任务状态 [eval_id={eval_id}]")
        return False
    
    try:
        # 保存状态（使用名称字符串而非整数值）
        redis_client.set(get_task_status_key(eval_id), status.name)
        # 发布通知（也使用名称字符串）
        redis_client.publish(get_task_channel(eval_id), status.name)
        
        # 保存消息和结果（如果有）
        if message:
            redis_client.set(get_task_message_key(eval_id), message)
        if result:
            try:
                redis_client.set(get_task_result_key(eval_id), json.dumps(result))
            except Exception as e:
                logger.warning(f"无法序列化结果: {str(e)}")
                redis_client.set(get_task_result_key(eval_id), str(result))
        
        logger.debug(f"已发布任务状态 [eval_id={eval_id}, status={status.name}]")
        return True
    except Exception as e:
        logger.error(f"发布任务状态失败 [eval_id={eval_id}]: {str(e)}")
        return False

def get_evaluation(eval_id: int) -> Optional[Evaluation]:
    """获取评估任务信息
    
    Args:
        eval_id: 评估ID
        
    Returns:
        Optional[Evaluation]: 评估信息或None
    """
    try:
        with DatabaseSessionManager.session() as db:
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            return evaluation
    except Exception as e:
        logger.error(f"获取评估信息失败 [eval_id={eval_id}]: {str(e)}")
        return None

@shared_task(bind=True, name="execute_evaluation_task")
def execute_evaluation_task(self, task_id: str, eval_id: int) -> Dict[str, Any]:
    """执行评估任务
    
    Args:
        task_id: Celery任务ID
        eval_id: 评估ID
        
    Returns:
        Dict[str, Any]: 执行结果
    """
    logger.info(f"开始执行评估任务 [eval_id={eval_id}, task_id={task_id}]")
    
    # 更新任务状态为运行中
    publish_task_status(eval_id, TaskStatus.RUNNING, "任务正在运行中")
    
    # 获取评估信息
    evaluation = get_evaluation(eval_id)
    if not evaluation:
        logger.error(f"找不到评估任务 [eval_id={eval_id}]")
        publish_task_status(eval_id, TaskStatus.FAILED, "找不到评估任务")
        return {"success": False, "message": "找不到评估任务"}
    
    try:
        # 创建并运行评估任务
        from apps.server.src.tasks.task_evaluator import TaskEvaluator
        
        # 使用TaskEvaluator
        evaluator = TaskEvaluator(self, eval_id)
        result = evaluator.execute()
        
        # 检查执行结果
        if result and result.get("status") == "RUNNING":
            # 任务正在运行中，这是正常的返回结果
            message = result.get("message", "任务已启动并在后台运行")
            logger.info(f"评估任务已启动并在后台运行 [eval_id={eval_id}]")
            
            # 更新Redis状态
            publish_task_status(eval_id, TaskStatus.RUNNING, message)
            
            return {
                "success": True, 
                "message": message, 
                "status": "RUNNING"
            }
            
        elif result.get("success", False):
            # 任务执行成功
            logger.info(f"评估任务执行成功 [eval_id={eval_id}]")
            
            # 更新Redis状态
            publish_task_status(
                eval_id,
                TaskStatus.COMPLETED,
                "任务执行完成",
                result.get("result")
            )
            
            return {
                "success": True,
                "result": result.get("result")
            }
            
        else:
            # 任务执行失败
            error_message = result.get("message", "任务执行失败")
            logger.error(f"评估任务执行失败 [eval_id={eval_id}]: {error_message}")
            
            # 更新Redis状态
            publish_task_status(
                eval_id,
                TaskStatus.FAILED,
                error_message,
                {"error": result.get("error")}
            )
            
            return {
                "success": False,
                "message": error_message
            }
            
    except Exception as e:
        # 处理异常
        error_msg = f"执行评估任务异常: {str(e)}"
        logger.exception(error_msg)
        
        # 更新Redis状态
        publish_task_status(
            eval_id,
            TaskStatus.FAILED,
            error_msg,
            {"error": traceback.format_exc()}
        )
        
        return {
            "success": False,
            "message": error_msg
        } 