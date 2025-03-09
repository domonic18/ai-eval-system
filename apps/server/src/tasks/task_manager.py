import os
import time
import logging
import threading
import queue
import concurrent.futures
from typing import Dict, List, Optional, Any, Tuple, Deque, Set
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
import json
import re

from sqlalchemy.orm import Session
from celery.result import AsyncResult
from sqlalchemy import text

from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus
from celery_app import celery_app
from tasks.task_eval import run_evaluation
from tasks.runners.runner import get_runner
from utils.redis_manager import RedisManager
from utils.utils_db import DatabaseSessionManager
import redis

# from apps.server.src.core.config import (
#     TASK_MANAGER_MAX_CONCURRENT_TASKS,
#     TASK_MANAGER_TASK_TIMEOUT_MINUTES,
#     TASK_MANAGER_CLEANUP_HOURS
# )

# 配置日志
logger = logging.getLogger(__name__)

# 使用单例模式实现全局任务管理器
class TaskManager:
    """简化后的任务管理器，仅保留状态跟踪"""
    
    def __init__(self):
        self.tasks = {}  # 仅保留任务状态缓存
        self.redis_client = RedisManager.get_instance()
        self.logger = logging.getLogger(__name__)

    def create_task(self, eval_id: int, db: Session) -> Dict[str, Any]:
        """使用Celery原生机制创建任务
        
        Args:
            eval_id: 评估ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 包含任务ID和状态的信息
        """
        try:
            # 获取评估记录
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if not evaluation:
                return {"success": False, "message": "Evaluation not found"}

            # 提交Celery任务
            from tasks.task_eval import run_evaluation  # 确保相对路径正确
            task = run_evaluation.apply_async(
                args=(eval_id,),  # 使用元组格式
                queue='eval_tasks',
                # priority=0,
                serializer='json'
            )

            # 更新数据库记录
            evaluation.task_id = task.id
            evaluation.status = EvaluationStatus.PENDING.value
            evaluation.updated_at = datetime.now()
            db.commit()

            return {
                "success": True,
                "task_id": task.id,
                "status": "PENDING",
                "message": "任务已提交到Celery队列"
            }

        except Exception as e:
            db.rollback()
            logger.exception(f"创建Celery任务失败 [eval_id={eval_id}]: {str(e)}")
            return {
                "success": False,
                "message": f"任务提交失败: {str(e)}",
                "error": str(e)
            }

    def get_task_status(self, eval_id: int) -> dict:
        """直接使用EvaluationStatus状态"""
        try:
            evaluation = self._get_db_evaluation(eval_id)
            if not evaluation:
                return {"status": EvaluationStatus.UNKNOWN.value}
            
            # 从Celery获取原生状态
            celery_status = AsyncResult(evaluation.task_id).status if evaluation.task_id else None
            
            # 映射Celery状态到EvaluationStatus
            status_mapping = {
                'PENDING': EvaluationStatus.PENDING,
                'STARTED': EvaluationStatus.RUNNING,
                'SUCCESS': EvaluationStatus.COMPLETED,
                'FAILURE': EvaluationStatus.FAILED,
                'REVOKED': EvaluationStatus.TERMINATED,
                'RETRY': EvaluationStatus.PENDING
            }
            
            return {
                "status": status_mapping.get(celery_status, EvaluationStatus.UNKNOWN).value,
                "task_id": evaluation.task_id,
                "eval_status": evaluation.status  # 数据库状态
            }
        except Exception as e:
            return {"error": str(e)}

    def terminate_task(self, eval_id: int) -> dict:
        """使用Celery原生终止功能"""
        evaluation = self._get_db_evaluation(eval_id)
        if not evaluation:
            return {"success": False, "message": "Task not found"}
            
        AsyncResult(evaluation.task_id).revoke(terminate=True)
        return {"success": True}

    def _get_db_evaluation(self, eval_id: int):
        """辅助方法获取数据库记录"""
        with SessionLocal() as db:
            return db.query(Evaluation).get(eval_id)
    