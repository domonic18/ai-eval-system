"""Celery任务实现

包含所有Celery异步任务的定义和实现
"""

import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime

from celery import shared_task
from sqlalchemy.orm import Session

from apps.server.src.celery_app import celery_app
from apps.server.src.db import SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.tasks.task_manager import TaskManager, TaskStatus

# 配置日志
logger = logging.getLogger(__name__)

def get_db_session() -> Session:
    """获取数据库会话"""
    return SessionLocal()

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
    
    # 获取任务管理器
    task_manager = TaskManager()
    
    # 更新任务状态为运行中
    task_manager.update_task_status(
        eval_id=eval_id,
        status=TaskStatus.RUNNING,
        metadata={"message": "任务正在运行中"}
    )
    
    # 在数据库中更新任务状态
    update_task_status(eval_id, EvaluationStatus.RUNNING, "任务执行中")
    
    try:
        # 获取评估信息
        with get_db_session() as db:
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            
            if not evaluation:
                logger.error(f"找不到评估任务 [eval_id={eval_id}]")
                # 更新任务状态为失败
                task_manager.update_task_status(
                    eval_id=eval_id,
                    status=TaskStatus.FAILED,
                    metadata={"message": "找不到评估任务"}
                )
                return {"success": False, "message": "找不到评估任务"}
            
            # 获取评估配置
            eval_config = evaluation.config
            
            # 创建并运行OpenCompass Runner
            from apps.server.src.tasks.eval_tasks import run_evaluation_internal
            from apps.server.src.tasks.task_evaluator import TaskEvaluator
            
            # 直接使用TaskEvaluator而不是run_evaluation_internal
            evaluator = TaskEvaluator(self, eval_id)
            result = evaluator.execute()
            
            # 检查执行结果
            if result and result.get("status") == "RUNNING":
                # 任务正在运行中，这是正常的返回结果
                logger.info(f"评估任务已启动并在后台运行 [eval_id={eval_id}]")
                
                # 确保数据库和Redis中状态为RUNNING
                update_task_status(eval_id, EvaluationStatus.RUNNING, result.get("message", "任务已启动并在后台运行"))
                
                # 不要在这里将TaskManager中的任务标记为COMPLETED
                # 由monitor_task线程在任务真正完成时更新状态
                return {"success": True, "message": result.get("message", "任务已启动"), "status": "RUNNING"}
            elif result.get("success", False):
                # 更新任务状态为完成
                task_manager.update_task_status(
                    eval_id=eval_id,
                    status=TaskStatus.COMPLETED,
                    metadata={
                        "message": "任务执行完成",
                        "result": result.get("result")
                    }
                )
                
                # 在数据库中更新任务状态
                update_task_status(eval_id, EvaluationStatus.COMPLETED, "任务执行完成")
                
                logger.info(f"评估任务执行成功 [eval_id={eval_id}]")
                return {"success": True, "result": result.get("result")}
            else:
                # 更新任务状态为失败
                task_manager.update_task_status(
                    eval_id=eval_id,
                    status=TaskStatus.FAILED,
                    metadata={
                        "message": result.get("message", "任务执行失败"),
                        "error": result.get("error")
                    }
                )
                
                # 在数据库中更新任务状态
                update_task_status(
                    eval_id, 
                    EvaluationStatus.FAILED, 
                    result.get("message", "任务执行失败")
                )
                
                logger.error(f"评估任务执行失败 [eval_id={eval_id}]: {result.get('message')}")
                return {"success": False, "message": result.get("message")}
                
    except Exception as e:
        error_msg = f"执行评估任务异常: {str(e)}\n{traceback.format_exc()}"
        logger.exception(error_msg)
        
        # 更新任务状态为失败
        try:
            task_manager.update_task_status(
                eval_id=eval_id,
                status=TaskStatus.FAILED,
                metadata={"message": f"执行异常: {str(e)}", "error": error_msg}
            )
        except Exception as update_error:
            logger.exception(f"更新任务状态失败: {str(update_error)}")
        
        # 在数据库中更新任务状态
        update_task_status(eval_id, EvaluationStatus.FAILED, f"执行异常: {str(e)}")
        
        return {"success": False, "message": f"执行异常: {str(e)}"}

def update_task_status(eval_id: int, status: EvaluationStatus, message: Optional[str] = None) -> bool:
    """更新评估任务状态
    
    Args:
        eval_id: 评估ID
        status: 新状态
        message: 可选的消息
        
    Returns:
        bool: 是否成功更新
    """
    try:
        with get_db_session() as db:
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            
            if not evaluation:
                logger.warning(f"找不到评估任务，无法更新状态 [eval_id={eval_id}]")
                return False
            
            evaluation.status = status
            if message:
                evaluation.message = message
            evaluation.updated_at = datetime.now()
            db.commit()
            
            return True
    except Exception as e:
        logger.exception(f"更新任务状态异常 [eval_id={eval_id}]: {str(e)}")
        return False 