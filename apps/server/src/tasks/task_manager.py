"""任务管理器

管理任务的创建、执行、状态追踪和终止。
实现任务队列和并发控制。
"""

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

from apps.server.src.db import SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.celery_app import celery_app
from apps.server.src.tasks.eval_tasks import run_evaluation
from apps.server.src.tasks.opencompass_runner import get_runner
from apps.server.src.utils.redis_manager import RedisManager
# 使用共享的任务状态模块
from apps.server.src.tasks.task_status import TaskStatus, format_task_status, get_celery_task_state, map_celery_state_to_task_status, safe_parse_task_status
from apps.server.src.utils.db_utils import DatabaseSessionManager
import redis

from apps.server.src.core.config import (
    TASK_MANAGER_MAX_CONCURRENT_TASKS,
    TASK_MANAGER_TASK_TIMEOUT_MINUTES,
    TASK_MANAGER_CLEANUP_HOURS
)

# 配置日志
logger = logging.getLogger(__name__)

# 任务状态和数据库状态映射
STATUS_MAPPING = {
    TaskStatus.PENDING: EvaluationStatus.PENDING,
    TaskStatus.WAITING: EvaluationStatus.PENDING,
    TaskStatus.QUEUED: EvaluationStatus.PENDING,
    TaskStatus.RUNNING: EvaluationStatus.RUNNING,
    TaskStatus.COMPLETED: EvaluationStatus.COMPLETED,
    TaskStatus.FAILED: EvaluationStatus.FAILED,
    TaskStatus.TERMINATED: EvaluationStatus.TERMINATED
}

# 使用单例模式实现全局任务管理器
class TaskManager:
    """任务管理器类
    
    管理所有任务的创建、执行和状态追踪
    实现任务队列和并发控制
    集成Celery分布式任务执行
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """获取TaskManager单例实例
        
        使用双重检查锁定模式（Double-Checked Locking Pattern）确保线程安全。
        添加超时机制避免长时间等待实例创建。
        
        Returns:
            TaskManager: 任务管理器单例实例
        """
        # 第一次检查（无锁）
        if cls._instance is None:
            # 设置超时机制
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("获取TaskManager实例超时")
            
            # 设置15秒超时
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(15)
            
            try:
                # 获取锁并创建实例
                with cls._lock:
                    # 第二次检查（有锁）
                    if cls._instance is None:
                        logger.info("创建TaskManager单例实例")
                        cls._instance = super(TaskManager, cls).__new__(cls)
                        cls._instance.__init__()
            finally:
                # 取消超时
                signal.alarm(0)
        
        # 确保实例已创建
        if cls._instance is None:
            logger.error("无法创建TaskManager实例，将创建临时降级实例")
            # 创建最基本的实例，避免返回None
            cls._instance = super(TaskManager, cls).__new__(cls)
            # 设置最小化属性，使其可用
            if not hasattr(cls._instance, 'tasks'):
                cls._instance.tasks = {}
            if not hasattr(cls._instance, 'active_tasks'):
                cls._instance.active_tasks = set()
            if not hasattr(cls._instance, 'waiting_queue'):
                cls._instance.waiting_queue = deque()
            if not hasattr(cls._instance, 'task_lock'):
                cls._instance.task_lock = threading.RLock()
            if not hasattr(cls._instance, 'fully_initialized'):
                cls._instance.fully_initialized = True
                
        return cls._instance
    
    def __new__(cls):
        """确保只有一个实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TaskManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化TaskManager单例"""
        self.tasks = {}
        self.waiting_queue = deque()
        self.logger = logging.getLogger(__name__)
        
        # 添加任务锁，用于线程安全访问
        self.task_lock = threading.RLock()
        
        # 设置最大并发任务数
        self.max_concurrent_tasks = TASK_MANAGER_MAX_CONCURRENT_TASKS
        
        # 获取Redis实例
        self.redis_client = RedisManager.get_instance()
        if not self.redis_client:
            self.logger.error("无法获取Redis客户端，任务管理功能将受到限制")
        
        # 任务监控线程
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        
        # Redis状态更新线程
        self.status_subscriber_thread = None
        
        # 初始化任务管理系统
        self.logger.info("初始化任务管理器")
        
        # 加载现有任务
        self._load_existing_tasks()
        
        # 启动任务监控线程
        self._start_monitor_thread()
        
        # 启动Redis状态监听线程
        self._start_status_subscriber()
        
        self.logger.info("任务管理器初始化完成")
        
    def _load_existing_tasks(self) -> None:
        """从数据库加载现有任务"""
        try:
            # 使用DatabaseSessionManager获取会话
            with DatabaseSessionManager.session() as db:
                # 获取所有未完成的任务
                running_tasks = db.query(Evaluation).filter(
                    Evaluation.status.in_([
                        EvaluationStatus.PENDING.value,
                        EvaluationStatus.RUNNING.value
                    ])
                ).all()
                
                for task in running_tasks:
                    # 创建任务信息
                    task_info = {
                        "id": task.id,
                        "status": TaskStatus.from_evaluation_status(EvaluationStatus(task.status)),
                        "celery_id": task.task_id,
                        "created_at": task.created_at,
                        "updated_at": task.updated_at,
                        "model_name": task.model_name,
                        "dataset_name": task.dataset_name,
                        "message": "从数据库恢复的任务"
                    }
                    
                    # 添加到任务字典
                    self.tasks[task.id] = task_info
                    
                    # 检查任务状态
                    if task.task_id:  # 有Celery任务ID
                        # 映射Celery任务ID到评估ID
                        self.celery_tasks[task.task_id] = task.id
                        
                        # 检查Celery任务状态
                        celery_state = get_celery_task_state(task.task_id)
                        if celery_state in ['STARTED', 'RETRY']:
                            task_info["status"] = TaskStatus.RUNNING
                        elif celery_state == 'SUCCESS':
                            task_info["status"] = TaskStatus.COMPLETED
                        elif celery_state == 'FAILURE':
                            task_info["status"] = TaskStatus.FAILED
                        elif celery_state == 'REVOKED':
                            task_info["status"] = TaskStatus.TERMINATED
                        else:  # PENDING或其他
                            # 将任务加入等待队列
                            task_info["status"] = TaskStatus.WAITING
                            self.waiting_queue.append(task.id)
                    else:  # 没有Celery任务ID
                        # 将任务加入等待队列
                        task_info["status"] = TaskStatus.WAITING
                        self.waiting_queue.append(task.id)
                
                logger.info(f"从数据库加载了 {len(running_tasks)} 个任务，当前等待队列长度: {len(self.waiting_queue)}")
        except Exception as e:
            logger.error(f"从数据库加载现有任务失败: {str(e)}")
            # 继续执行，不影响任务管理器的初始化
    
    def create_task(self, eval_id: int, db: Session) -> Dict[str, Any]:
        """创建并提交任务
        
        Args:
            eval_id: 评估ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 包含任务ID和状态的信息
        """
        with self.task_lock:
            # 检查任务是否已存在
            if eval_id in self.tasks:
                logger.warning(f"任务已存在 [eval_id={eval_id}]")
                return {
                    "success": False,
                    "message": "任务已存在",
                    "task_id": self.tasks[eval_id].get("celery_id"),
                    "status": self.tasks[eval_id].get("status")
                }
            
            # 创建任务记录
            task_info = {
                "eval_id": eval_id,
                "celery_id": None,
                "status": TaskStatus.PENDING,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "message": "任务已创建"
            }
            
            # 保存任务信息
            self.tasks[eval_id] = task_info
            
            # 更新数据库状态
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if evaluation:
                evaluation.status = task_info["status"].to_evaluation_status()
                evaluation.message = task_info["message"]
                evaluation.updated_at = datetime.now()
                db.commit()
            
            # 检查是否可以立即执行任务
            if len(self.active_tasks) < self.max_concurrent_tasks:
                # 可以立即执行
                return self._execute_task(eval_id, db)
            else:
                # 加入等待队列
                logger.info(f"当前活动任务数已达上限({len(self.active_tasks)}/{self.max_concurrent_tasks})，任务加入等待队列 [eval_id={eval_id}]")
                self.waiting_queue.append(eval_id)
                
                # 更新任务状态为等待中
                task_info["status"] = TaskStatus.WAITING
                task_info["message"] = "任务已加入等待队列"
                task_info["updated_at"] = datetime.now()
                
                # 更新数据库状态
                if evaluation:
                    evaluation.message = "任务等待中，前方队列任务数: {}".format(len(self.waiting_queue) - 1)
                    evaluation.updated_at = datetime.now()
                    db.commit()
                
                return {
                    "success": True,
                    "task_id": None,
                    "status": TaskStatus.WAITING,
                    "message": "任务已加入等待队列",
                    "queue_position": len(self.waiting_queue) - 1  # 队列位置（0是队首）
                }
    
    def _execute_task(self, eval_id: int, db: Session) -> Dict[str, Any]:
        """执行任务（内部方法）
        
        Args:
            eval_id: 评估ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            # 获取任务信息
            task_info = self.tasks[eval_id]
            
            # 在局部导入execute_evaluation_task避免循环导入
            from apps.server.src.tasks.celery_tasks import execute_evaluation_task
            # 使用Celery提交任务
            celery_task = execute_evaluation_task.delay(None, eval_id)
            
            # 更新任务信息
            task_info["celery_id"] = celery_task.id
            task_info["status"] = TaskStatus.QUEUED
            task_info["message"] = "任务已提交到执行队列"
            task_info["updated_at"] = datetime.now()
            
            # 更新Celery任务映射
            self.celery_tasks[celery_task.id] = eval_id
            
            # 添加到活动任务集合
            self.active_tasks.add(eval_id)
            
            # 更新数据库状态
            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if evaluation:
                evaluation.task_id = celery_task.id
                evaluation.message = task_info["message"]
                evaluation.updated_at = datetime.now()
                db.commit()
            
            logger.info(f"任务已提交执行 [eval_id={eval_id}, celery_id={celery_task.id}], 当前活动任务数: {len(self.active_tasks)}/{self.max_concurrent_tasks}")
            
            return {
                "success": True,
                "task_id": celery_task.id,
                "status": task_info["status"],
                "message": task_info["message"]
            }
        except Exception as e:
            logger.exception(f"提交任务异常 [eval_id={eval_id}]: {str(e)}")
            
            # 更新任务状态为失败
            task_info = self.tasks[eval_id]
            task_info["status"] = TaskStatus.FAILED
            task_info["message"] = f"提交任务失败: {str(e)}"
            task_info["updated_at"] = datetime.now()
            task_info["error"] = str(e)
            
            # 更新数据库状态
            try:
                evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                if evaluation:
                    evaluation.status = EvaluationStatus.FAILED
                    evaluation.message = task_info["message"]
                    evaluation.updated_at = datetime.now()
                    db.commit()
            except Exception as db_error:
                logger.exception(f"更新数据库状态异常 [eval_id={eval_id}]: {str(db_error)}")
            
            # 执行失败后，尝试调度下一个任务
            self._schedule_next_task(db)
            
            return {
                "success": False,
                "message": f"提交任务失败: {str(e)}",
                "status": task_info["status"]
            }
    
    def _schedule_next_task(self, db: Session) -> bool:
        """调度下一个等待中的任务
        
        Args:
            db: 数据库会话
            
        Returns:
            bool: 是否成功调度
        """
        with self.task_lock:
            # 如果没有等待的任务，或者活动任务已达最大值，则不调度
            if (not self.waiting_queue) or len(self.active_tasks) >= self.max_concurrent_tasks:
                return False
                
            # 获取队列中的下一个任务
            try:
                next_eval_id = self.waiting_queue.popleft()
                
                # 检查任务是否仍然存在
                if next_eval_id not in self.tasks:
                    logger.warning(f"调度的任务不存在 [eval_id={next_eval_id}]")
                    # 继续尝试调度下一个任务
                    return self._schedule_next_task(db)
                
                # 检查任务是否为等待状态
                task_info = self.tasks[next_eval_id]
                if task_info["status"] != TaskStatus.WAITING:
                    logger.warning(f"调度的任务不是等待状态 [eval_id={next_eval_id}, status={task_info['status']}]")
                    # 继续尝试调度下一个任务
                    return self._schedule_next_task(db)
                
                # 执行任务
                logger.info(f"从等待队列调度任务 [eval_id={next_eval_id}], 当前等待任务数: {len(self.waiting_queue)}")
                with SessionLocal() as db:
                    self._execute_task(next_eval_id, db)
                
                # 更新其他等待任务的信息
                self._update_waiting_tasks(db)
                
                return True
            except Exception as e:
                logger.exception(f"调度任务异常: {str(e)}")
                return False
    
    def _update_waiting_tasks(self, db: Session) -> None:
        """更新等待队列中的任务信息
        
        更新每个等待任务的队列位置信息
        
        Args:
            db: 数据库会话
        """
        try:
            # 获取等待队列中的任务
            for i, eval_id in enumerate(self.waiting_queue):
                # 更新数据库任务信息
                evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                if evaluation:
                    evaluation.message = f"任务等待中，前方队列任务数: {i}"
                    evaluation.updated_at = datetime.now()
            
            # 一次性提交所有更新
            db.commit()
        except Exception as e:
            logger.exception(f"更新等待任务信息异常: {str(e)}")
            db.rollback()
    
    def get_task_status(self, eval_id: int) -> Dict[str, Any]:
        """获取任务状态
        
        Args:
            eval_id: 评估ID
            
        Returns:
            Dict[str, Any]: 任务状态信息
        """
        with self.task_lock:
            # 检查任务是否存在
            if eval_id not in self.tasks:
                logger.warning(f"任务不存在 [eval_id={eval_id}]")
                return {
                    "success": False,
                    "message": "任务不存在",
                    "status": None
                }
            
            task_info = self.tasks[eval_id]
            celery_id = task_info.get("celery_id")
            
            # 如果有Celery任务ID，且任务不是等待中的，则查询Celery任务状态
            if celery_id and task_info["status"] not in [TaskStatus.PENDING, TaskStatus.WAITING]:
                try:
                    # 获取Celery任务结果
                    result = AsyncResult(celery_id)
                    celery_status = result.status
                    
                    # 更新任务状态
                    if celery_status == 'SUCCESS':
                        # 不要自动将任务标记为COMPLETED
                        # 只有当任务真正完成时，monitor_task才会更新状态
                        # 这里只记录Celery任务已返回
                        logger.debug(f"Celery任务已返回 [eval_id={eval_id}, celery_id={celery_id}]")
                        
                        # 检查任务是否仍在运行中
                        with SessionLocal() as db:
                            evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                            if evaluation and evaluation.status == EvaluationStatus.RUNNING.value:
                                # 任务仍在运行中，保持状态
                                task_info["message"] = "任务正在后台运行中"
                            elif evaluation and evaluation.status == EvaluationStatus.COMPLETED.value:
                                # 任务已完成，更新状态
                                task_info["status"] = TaskStatus.COMPLETED
                                # 如果任务已完成，从活动任务中移除
                                if eval_id in self.active_tasks:
                                    self.active_tasks.remove(eval_id)
                                    # 调度下一个任务
                                    with SessionLocal() as session:
                                        self._schedule_next_task(session)
                    elif celery_status == 'FAILURE':
                        task_info["status"] = TaskStatus.FAILED
                        # 如果任务已失败，从活动任务中移除
                        if eval_id in self.active_tasks:
                            self.active_tasks.remove(eval_id)
                            # 调度下一个任务
                            with SessionLocal() as session:
                                self._schedule_next_task(session)
                    elif celery_status == 'REVOKED':
                        task_info["status"] = TaskStatus.TERMINATED
                        # 如果任务已终止，从活动任务中移除
                        if eval_id in self.active_tasks:
                            self.active_tasks.remove(eval_id)
                            # 调度下一个任务
                            with SessionLocal() as session:
                                self._schedule_next_task(session)
                    elif celery_status == 'STARTED':
                        task_info["status"] = TaskStatus.RUNNING
                    elif celery_status == 'PENDING':
                        # 保持当前状态，可能是PENDING或QUEUED
                        pass
                    
                    task_info["celery_status"] = celery_status
                    task_info["updated_at"] = datetime.now()
                except Exception as e:
                    logger.exception(f"获取Celery任务状态异常 [eval_id={eval_id}, celery_id={celery_id}]: {str(e)}")
            
            # 从runner获取更多详细信息
            runner_info = {}
            try:
                runner = get_runner(eval_id)
                if runner:
                    runner_info = {
                        "progress": runner.progress,
                        "running": runner.running,
                        "exit_code": runner.exit_code
                    }
            except Exception as e:
                logger.exception(f"获取runner信息异常 [eval_id={eval_id}]: {str(e)}")
            
            # 构建响应
            response = {
                "success": True,
                "eval_id": eval_id,
                "status": task_info["status"],
                "message": task_info.get("message", ""),
                "celery_id": celery_id,
                "created_at": task_info["created_at"],
                "updated_at": task_info["updated_at"]
            }
            
            # 如果是等待中的任务，添加队列位置信息
            if task_info["status"] == TaskStatus.WAITING:
                try:
                    queue_position = list(self.waiting_queue).index(eval_id)
                    response["queue_position"] = queue_position
                except ValueError:
                    # 任务不在队列中，可能是状态不一致
                    response["queue_position"] = -1
            
            # 添加runner信息
            if runner_info:
                response["runner_info"] = runner_info
                
            return response
    
    def terminate_task(self, eval_id: int) -> Dict[str, Any]:
        """终止任务
        
        Args:
            eval_id: 评估ID
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        with self.task_lock:
            # 检查任务是否存在
            if eval_id not in self.tasks:
                logger.warning(f"任务不存在，无法终止 [eval_id={eval_id}]")
                return {
                    "success": False,
                    "message": "任务不存在，无法终止"
                }
            
            task_info = self.tasks[eval_id]
            celery_id = task_info.get("celery_id")
            
            # 如果任务已完成或已失败或已终止，则无需终止
            if task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TERMINATED]:
                logger.info(f"任务已处于最终状态，无需终止 [eval_id={eval_id}, status={task_info['status']}]")
                return {
                    "success": True,
                    "message": f"任务已处于最终状态: {task_info['status']}"
                }
            
            # 如果任务处于等待状态，直接从等待队列中移除
            if task_info["status"] == TaskStatus.WAITING:
                try:
                    self.waiting_queue.remove(eval_id)
                    logger.info(f"已从等待队列移除任务 [eval_id={eval_id}]")
                    
                    # 更新任务状态为已终止
                    task_info["status"] = TaskStatus.TERMINATED
                    task_info["message"] = "任务已取消"
                    task_info["updated_at"] = datetime.now()
                    
                    # 更新数据库状态
                    with SessionLocal() as db:
                        evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                        if evaluation:
                            evaluation.status = EvaluationStatus.TERMINATED
                            evaluation.message = "任务已取消"
                            evaluation.updated_at = datetime.now()
                            db.commit()
                            
                            # 更新其他等待任务的信息
                            self._update_waiting_tasks(db)
                    
                    return {
                        "success": True,
                        "message": "等待中的任务已取消"
                    }
                except ValueError:
                    # 任务不在队列中，可能是状态不一致
                    logger.warning(f"等待中的任务不在队列中 [eval_id={eval_id}]")
                except Exception as e:
                    logger.exception(f"取消等待任务异常 [eval_id={eval_id}]: {str(e)}")
            
            # 终止Celery任务
            success = False
            try:
                if celery_id:
                    # 撤销Celery任务
                    result = AsyncResult(celery_id)
                    result.revoke(terminate=True)
                    logger.info(f"已撤销Celery任务 [eval_id={eval_id}, celery_id={celery_id}]")
                
                # 终止runner
                runner = get_runner(eval_id)
                if runner:
                    runner.terminate()
                    logger.info(f"已终止Runner [eval_id={eval_id}]")
                
                # 更新任务状态
                task_info["status"] = TaskStatus.TERMINATED
                task_info["message"] = "任务已终止"
                task_info["updated_at"] = datetime.now()
                
                success = True
                
                # 从活动任务中移除
                if eval_id in self.active_tasks:
                    self.active_tasks.remove(eval_id)
                    logger.info(f"已从活动任务移除 [eval_id={eval_id}], 当前活动任务数: {len(self.active_tasks)}/{self.max_concurrent_tasks}")
                    
                    # 更新数据库状态
                    with SessionLocal() as db:
                        evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                        if evaluation:
                            evaluation.status = EvaluationStatus.TERMINATED
                            evaluation.message = "任务已终止"
                            evaluation.updated_at = datetime.now()
                            db.commit()
                        
                        # 调度下一个任务
                        self._schedule_next_task(db)
            except Exception as e:
                logger.exception(f"终止任务异常 [eval_id={eval_id}]: {str(e)}")
                return {
                    "success": False,
                    "message": f"终止任务异常: {str(e)}"
                }
            
            return {
                "success": success,
                "message": "任务已终止"
            }
    
    def update_task_status(self, eval_id: int, status: TaskStatus, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """更新任务状态
        
        更新任务的状态和相关元数据，同时同步到Redis
        
        Args:
            eval_id: 评估ID
            status: 新的任务状态
            metadata: 额外元数据
            
        Returns:
            bool: 更新是否成功
        """
        with self.task_lock:
            # 确保任务存在
            if eval_id not in self.tasks:
                logger.warning(f"尝试更新不存在的任务状态 [eval_id={eval_id}]")
                return False
            
            task_info = self.tasks[eval_id]
            old_status = task_info["status"]
            
            # 更新状态
            task_info["status"] = status
            task_info["updated_at"] = datetime.now()
            
            # 更新消息
            if metadata and "message" in metadata:
                task_info["message"] = metadata["message"]
                
            # 添加结果（如果有）
            if metadata and "result" in metadata:
                task_info["result"] = metadata["result"]
                
            # 保存到Redis
            self.save_task_status_to_redis(eval_id, status, metadata)
                
            # 更新数据库状态
            try:
                # 将评估状态映射到数据库状态
                db_status = None
                if status == TaskStatus.COMPLETED:
                    db_status = EvaluationStatus.COMPLETED
                elif status == TaskStatus.FAILED:
                    db_status = EvaluationStatus.FAILED
                elif status == TaskStatus.TERMINATED:
                    db_status = EvaluationStatus.TERMINATED
                elif status in [TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING]:
                    db_status = EvaluationStatus.RUNNING
                
                if db_status:
                    with SessionLocal() as db:
                        evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                        if evaluation:
                            evaluation.status = db_status.value
                            if metadata and "message" in metadata:
                                if db_status == EvaluationStatus.FAILED:
                                    evaluation.error_message = metadata["message"]
                            
                            if metadata and "progress" in metadata:
                                evaluation.progress = metadata["progress"]
                                
                            if metadata and "result" in metadata and status == TaskStatus.COMPLETED:
                                evaluation.results = json.dumps(metadata["result"])
                                
                            evaluation.updated_at = datetime.now()
                            db.commit()
            except Exception as e:
                logger.error(f"更新数据库任务状态失败 [eval_id={eval_id}]: {str(e)}")
                
            # 记录状态变更日志
            log_message = f"任务状态已更新 [eval_id={eval_id}]: {old_status.name} -> {status.name}"
            if metadata and "message" in metadata:
                log_message += f", 消息: {metadata['message']}"
            logger.info(log_message)
            
            return True
    
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        """列出任务
        
        Args:
            status: 可选的状态过滤条件
            
        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        with self.task_lock:
            result = []
            
            for eval_id, task_info in self.tasks.items():
                # 如果指定了状态过滤，则跳过不匹配的任务
                if status and task_info["status"] != status:
                    continue
                
                # 构建任务信息
                task_data = {
                    "eval_id": eval_id,
                    "celery_id": task_info.get("celery_id"),
                    "status": task_info["status"],
                    "message": task_info.get("message", ""),
                    "created_at": task_info["created_at"],
                    "updated_at": task_info["updated_at"]
                }
                
                # 如果是等待中的任务，添加队列位置信息
                if task_info["status"] == TaskStatus.WAITING:
                    try:
                        queue_position = list(self.waiting_queue).index(eval_id)
                        task_data["queue_position"] = queue_position
                    except ValueError:
                        task_data["queue_position"] = -1
                
                result.append(task_data)
            
            return result
    
    def get_queue_info(self) -> Dict[str, Any]:
        """获取队列状态信息
        
        Returns:
            Dict[str, Any]: 队列状态
        """
        with self.task_lock:
            return {
                "active_tasks": len(self.active_tasks),
                "waiting_tasks": len(self.waiting_queue),
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "active_task_ids": list(self.active_tasks),
                "waiting_task_ids": list(self.waiting_queue)
            }
    
    def _get_max_concurrent_tasks(self) -> int:
        """获取最大并发任务数
        
        从配置中读取最大并发任务数，如果配置中没有设置，则使用默认值10
        
        返回:
            int: 最大并发任务数
        """
        try:
            return TASK_MANAGER_MAX_CONCURRENT_TASKS
        except Exception as e:
            logger.warning(f"读取最大并发任务数配置失败: {str(e)}，使用默认值10")
            return 10
    
    def clean_tasks(self, max_age_hours: int = None) -> int:
        """清理旧任务
        
        Args:
            max_age_hours: 任务最大保留时间（小时）
            
        Returns:
            int: 清理的任务数量
        """
        # 如果没有指定max_age_hours，则从配置中获取
        if max_age_hours is None:
            max_age_hours = TASK_MANAGER_CLEANUP_HOURS
            
        try:
            # 计算截止时间
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            tasks_to_remove = []
            
            # 查找需要移除的旧任务
            for eval_id, task_info in self.tasks.items():
                if task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TERMINATED]:
                    updated_at = task_info.get("updated_at")
                    if updated_at and updated_at < cutoff_time:
                        tasks_to_remove.append(eval_id)
            
            # 从内存中删除旧任务
            for eval_id in tasks_to_remove:
                if eval_id in self.tasks:
                    del self.tasks[eval_id]
                    if eval_id in self.active_tasks:
                        self.active_tasks.remove(eval_id)
            
            # 从数据库中清理旧的已完成或失败的评估记录
            try:
                # 数据库操作添加超时机制
                db_cleaned = 0
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    db_clean_future = executor.submit(self._clean_db_tasks, cutoff_time)
                    try:
                        db_cleaned = db_clean_future.result(timeout=15)  # 15秒超时
                    except concurrent.futures.TimeoutError:
                        logger.warning("清理数据库任务超时")
                
                return len(tasks_to_remove) + db_cleaned
            except Exception as e:
                logger.error(f"清理数据库任务失败: {str(e)}")
                return len(tasks_to_remove)  # 至少返回内存中清理的数量
                
        except Exception as e:
            logger.error(f"清理任务异常: {str(e)}")
            return 0

    def _clean_db_tasks(self, cutoff_time):
        """从数据库中清理旧任务"""
        cleaned = 0
        try:
            with SessionLocal() as db:
                # 查询所有过期的已完成或失败的评估
                old_evaluations = db.query(Evaluation).filter(
                    Evaluation.updated_at < cutoff_time,
                    Evaluation.status.in_([
                        EvaluationStatus.COMPLETED.value,
                        EvaluationStatus.FAILED.value,
                        EvaluationStatus.TERMINATED.value
                    ])
                ).all()
                
                # 删除过期的评估
                for evaluation in old_evaluations:
                    db.delete(evaluation)
                    cleaned += 1
                
                db.commit()
                return cleaned
        except Exception as e:
            logger.error(f"数据库清理失败: {str(e)}")
            return 0
            
    def check_database_connection(self):
        """检查数据库连接状态
        
        Returns:
            bool: 连接正常返回True，否则返回False
        """
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._try_db_connection)
                try:
                    return future.result(timeout=5)  # 5秒超时
                except concurrent.futures.TimeoutError:
                    logger.error("数据库连接检查超时")
                    return False
        except Exception as e:
            logger.error(f"检查数据库连接失败: {str(e)}")
            return False
            
    def _try_db_connection(self):
        """尝试建立数据库连接"""
        try:
            with SessionLocal() as db:
                # 执行简单查询测试连接
                result = db.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            return False
    
    def _start_monitor_thread(self):
        """启动任务监控线程"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.warning("监控线程已经在运行中")
            return
        
        # 启动监控线程
        self.monitor_thread = threading.Thread(
            target=self._monitor_tasks,
            daemon=True,
            name="TaskManager-Monitor"
        )
        self.monitor_thread.start()
        self.logger.info("已启动任务监控线程")

    def _monitor_tasks(self):
        """监控任务状态及执行情况
        
        定期检查任务状态，处理超时任务，并尝试启动等待队列中的任务
        """
        self.logger.info("任务监控线程已启动")
        
        while not self.stop_monitoring.is_set():
            try:
                # 处理等待队列中的任务
                self._process_waiting_tasks()
                
                # 检查活跃任务的状态
                self._check_active_tasks()
                
                # 清理已完成的任务
                self._clean_completed_tasks()
                
            except Exception as e:
                self.logger.exception(f"任务监控异常: {str(e)}")
            
            # 等待一段时间再次检查
            time.sleep(10)
        
        self.logger.info("任务监控线程已退出")

    def _process_waiting_tasks(self):
        """处理等待队列中的任务"""
        # 检查是否有空余的任务槽
        max_tasks = self._get_max_concurrent_tasks()
        current_active = len(self.active_tasks) if hasattr(self, 'active_tasks') else 0
        
        if not hasattr(self, 'waiting_queue'):
            self.waiting_queue = deque()
            
        if not hasattr(self, 'active_tasks'):
            self.active_tasks = set()
            
        if not hasattr(self, 'celery_tasks'):
            self.celery_tasks = {}
        
        # 如果有空余槽位且等待队列不为空
        while current_active < max_tasks and self.waiting_queue:
            try:
                # 获取下一个等待任务
                eval_id = self.waiting_queue.popleft()
                
                # 执行任务（添加缺失的db参数）
                with SessionLocal() as db:
                    self._execute_task(eval_id, db)
                
                # 更新活跃任务计数
                current_active += 1
                
                self.logger.info(f"已从等待队列启动任务 [eval_id={eval_id}]")
            except Exception as e:
                self.logger.exception(f"启动等待任务失败: {str(e)}")
                break

    def _check_active_tasks(self):
        """检查活跃任务的状态"""
        # 确保active_tasks属性存在
        if not hasattr(self, 'active_tasks'):
            self.active_tasks = set()
            return
        
        # 复制活跃任务集合以避免迭代时修改
        active_tasks = self.active_tasks.copy()
        
        for eval_id in active_tasks:
            try:
                # 获取任务状态
                status = self.get_task_status_from_redis(eval_id)
                
                if not status:
                    continue
                
                task_status = status.get("status")
                
                # 处理已完成或失败的任务
                if task_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TERMINATED]:
                    # 从活跃任务中移除
                    if eval_id in self.active_tasks:
                        self.active_tasks.remove(eval_id)
                    
                    self.logger.info(f"任务已完成或终止 [eval_id={eval_id}, status={task_status.name}]")
            except Exception as e:
                self.logger.exception(f"检查任务状态异常 [eval_id={eval_id}]: {str(e)}")

    def _clean_completed_tasks(self):
        """清理长时间完成的任务记录"""
        # 确保任务字典存在
        if not hasattr(self, 'tasks'):
            self.tasks = {}
            return
        
        # 获取当前时间
        now = datetime.now()
        cleanup_hours = 24  # 默认24小时后清理
        
        # 待清理的任务ID列表
        to_clean = []
        
        # 查找需要清理的任务
        for eval_id, task_info in self.tasks.items():
            # 只检查已完成或失败的任务
            if task_info.get("status") not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TERMINATED]:
                continue
            
            # 检查完成时间
            completed_at = task_info.get("completed_at")
            if not completed_at:
                continue
            
            # 计算时间差
            time_diff = now - completed_at
            if time_diff.total_seconds() > cleanup_hours * 3600:
                to_clean.append(eval_id)
        
        # 清理任务
        for eval_id in to_clean:
            try:
                # 从内存中删除
                del self.tasks[eval_id]
                
                # 从Redis中删除
                self.delete_task_status_from_redis(eval_id)
                
                self.logger.info(f"已清理过期任务 [eval_id={eval_id}]")
            except Exception as e:
                self.logger.exception(f"清理任务异常 [eval_id={eval_id}]: {str(e)}")

    #-------------------------
    # Redis状态管理方法
    #-------------------------
    
    def _get_task_status_key(self, eval_id: int) -> str:
        """获取任务状态在Redis中的键名
        
        Args:
            eval_id: 评估ID
            
        Returns:
            str: Redis键名
        """
        return f"task_status:{eval_id}"
    
    def _get_task_result_key(self, eval_id: int) -> str:
        """获取任务结果在Redis中的键名
        
        Args:
            eval_id: 评估ID
            
        Returns:
            str: Redis键名
        """
        return f"task_result:{eval_id}"
        
    def _get_task_message_key(self, eval_id: int) -> str:
        """获取任务消息在Redis中的键名
        
        Args:
            eval_id: 评估ID
            
        Returns:
            str: Redis键名
        """
        return f"task_message:{eval_id}"
    
    def save_task_status_to_redis(self, eval_id: int, status: TaskStatus, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """将任务状态保存到Redis
        
        Args:
            eval_id: 评估ID
            status: 任务状态
            metadata: 额外信息
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self.redis_client:
                logger.warning("Redis未连接，无法保存任务状态")
                return False
                
            # 保存任务状态（使用名称字符串而非整数值）
            status_key = self._get_task_status_key(eval_id)
            self.redis_client.set(status_key, status.name)
            
            # 保存任务消息
            if metadata and "message" in metadata:
                message_key = self._get_task_message_key(eval_id)
                self.redis_client.set(message_key, metadata["message"])
                
            # 保存任务结果
            if metadata and "result" in metadata:
                result_key = self._get_task_result_key(eval_id)
                self.redis_client.set(result_key, json.dumps(metadata["result"]))
                
            # 发布状态更新通知（也使用名称字符串）
            channel = f"task_status:{eval_id}"
            self.redis_client.publish(channel, status.name)
            
            return True
        except Exception as e:
            logger.error(f"保存任务状态到Redis失败 [eval_id={eval_id}]: {str(e)}")
            return False
    
    def get_task_status_from_redis(self, eval_id: int) -> Optional[Dict[str, Any]]:
        """从Redis获取任务状态
        
        Args:
            eval_id: 评估ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务状态信息
        """
        try:
            if not self.redis_client:
                logger.warning("Redis未连接，无法获取任务状态")
                return None
                
            # 获取任务状态
            status_key = self._get_task_status_key(eval_id)
            status_value = self.redis_client.get(status_key)
            
            if not status_value:
                return None
                
            # 获取任务消息
            message_key = self._get_task_message_key(eval_id)
            message = self.redis_client.get(message_key)
            
            # 获取任务结果
            result_key = self._get_task_result_key(eval_id)
            result_json = self.redis_client.get(result_key)
            result = json.loads(result_json) if result_json else None
            
            return {
                "status": safe_parse_task_status(status_value),
                "message": message,
                "result": result
            }
        except Exception as e:
            logger.error(f"从Redis获取任务状态失败 [eval_id={eval_id}]: {str(e)}")
            return None
    
    def delete_task_status_from_redis(self, eval_id: int) -> bool:
        """从Redis删除任务状态
        
        Args:
            eval_id: 评估ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self.redis_client:
                logger.warning("Redis未连接，无法删除任务状态")
                return False
                
            # 删除相关键
            status_key = self._get_task_status_key(eval_id)
            message_key = self._get_task_message_key(eval_id)
            result_key = self._get_task_result_key(eval_id)
            
            self.redis_client.delete(status_key, message_key, result_key)
            return True
        except Exception as e:
            logger.error(f"从Redis删除任务状态失败 [eval_id={eval_id}]: {str(e)}")
            return False
    
    def subscribe_task_status(self):
        """订阅任务状态更新
        
        返回:
            PubSub: Redis PubSub对象，如果失败则返回None
        """
        try:
            if not self.redis_client:
                logger.error("Redis客户端未初始化，无法订阅任务状态更新")
                return None
                
            pubsub = self.redis_client.pubsub()
            pubsub.psubscribe("task:*:update")
            logger.info("已订阅任务状态更新通道")
            return pubsub
        except Exception as e:
            logger.error(f"订阅任务状态更新失败: {str(e)}")
            return None
    
    def _start_status_subscriber(self):
        """启动Redis任务状态更新监听线程"""
        if not self.redis_client:
            self.logger.error("Redis客户端不可用，无法启动任务状态订阅")
            return
        
        def status_listener():
            """任务状态监听线程函数"""
            try:
                self.logger.info("启动Redis任务状态订阅线程")
                pubsub = self.redis_client.pubsub()
                
                # 订阅所有任务状态更新通道
                pubsub.psubscribe("task:*:update")
                
                # 接收和处理消息
                for message in pubsub.listen():
                    if self.stop_monitoring.is_set():
                        break
                    
                    try:
                        # 只处理消息类型
                        if message["type"] == "pmessage":
                            # 处理channel和data，注意它们可能已经是字符串类型
                            channel = message["channel"]
                            if isinstance(channel, bytes):
                                channel = channel.decode("utf-8")
                                
                            data = message["data"]
                            if isinstance(data, bytes):
                                data = data.decode("utf-8")
                            
                            # 提取eval_id (格式: "task:123:update")
                            match = re.search(r"task:(\d+):update", channel)
                            if match:
                                eval_id = int(match.group(1))
                                status_value = data
                                
                                # 从Redis获取附加信息
                                task_status_key = f"task:{eval_id}:status"
                                task_message_key = f"task:{eval_id}:message"
                                task_result_key = f"task:{eval_id}:result"
                                
                                # 获取状态消息
                                message = None
                                try:
                                    message_bytes = self.redis_client.get(task_message_key)
                                    if message_bytes:
                                        if isinstance(message_bytes, bytes):
                                            message = message_bytes.decode("utf-8")
                                        else:
                                            message = message_bytes
                                except Exception as e:
                                    self.logger.warning(f"获取任务消息失败 [eval_id={eval_id}]: {str(e)}")
                                
                                # 获取任务结果
                                result = None
                                try:
                                    result_bytes = self.redis_client.get(task_result_key)
                                    if result_bytes:
                                        if isinstance(result_bytes, bytes):
                                            result_str = result_bytes.decode("utf-8")
                                        else:
                                            result_str = result_bytes
                                        try:
                                            result = json.loads(result_str)
                                        except json.JSONDecodeError:
                                            result = result_str
                                except Exception as e:
                                    self.logger.warning(f"获取任务结果失败 [eval_id={eval_id}]: {str(e)}")
                                
                                # 将Redis状态转换为TaskStatus
                                try:
                                    # 添加调试日志
                                    self.logger.info(f"获取到的状态值类型: {type(status_value)}, 值: {status_value}")
                                    
                                    # 使用安全解析函数
                                    status = safe_parse_task_status(status_value)
                                    
                                    # 更新数据库状态
                                    self._update_db_status(eval_id, status, message, result)
                                    
                                    self.logger.info(f"任务状态已更新 [eval_id={eval_id}, status={status.name}]")
                                except Exception as e:
                                    self.logger.error(f"处理任务状态更新失败 [eval_id={eval_id}, value={status_value}]: {str(e)}")
                    except Exception as e:
                        self.logger.exception(f"处理任务状态更新异常: {str(e)}")
                
                self.logger.info("Redis任务状态订阅线程已退出")
            except Exception as e:
                self.logger.exception(f"Redis任务状态监听异常: {str(e)}")
        
        # 启动监听线程
        self.status_subscriber_thread = threading.Thread(
            target=status_listener,
            name="TaskStatusSubscriber",
            daemon=True
        )
        self.status_subscriber_thread.start()
        self.logger.info("Redis任务状态监听线程已启动")

    def _update_db_status(self, eval_id: int, status: TaskStatus, message: Optional[str] = None, result: Any = None):
        """将Redis状态更新同步到数据库
        
        Args:
            eval_id: 评估ID
            status: 任务状态
            message: 可选消息
            result: 可选结果数据
        """
        try:
            # 获取对应的数据库状态
            db_status = STATUS_MAPPING.get(status, EvaluationStatus.PENDING)
            
            # 更新数据库
            with DatabaseSessionManager.session() as db:
                evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                
                if not evaluation:
                    self.logger.warning(f"找不到评估任务，无法更新数据库状态 [eval_id={eval_id}]")
                    return
                
                # 更新状态和消息
                evaluation.status = db_status
                if message:
                    evaluation.message = message
                
                # 对于已完成的任务，更新结果
                if status == TaskStatus.COMPLETED and result:
                    # 如果结果是字符串，直接使用；否则尝试转换为JSON
                    if isinstance(result, str):
                        evaluation.result = result
                    else:
                        try:
                            evaluation.result = json.dumps(result)
                        except Exception as e:
                            self.logger.warning(f"结果序列化失败 [eval_id={eval_id}]: {str(e)}")
                            evaluation.result = str(result)
                
                # 更新时间
                evaluation.updated_at = datetime.now()
                
                # 提交更改
                db.commit()
                
                self.logger.debug(f"数据库状态已更新 [eval_id={eval_id}, status={db_status.name}]")
        except Exception as e:
            self.logger.exception(f"更新数据库状态异常 [eval_id={eval_id}]: {str(e)}")

    def shutdown(self):
        """关闭任务管理器"""
        self.logger.info("正在关闭任务管理器...")
        
        # 停止监控
        self.stop_monitoring.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
            if self.monitor_thread.is_alive():
                self.logger.warning("任务监控线程未能正常关闭")
        
        if self.status_subscriber_thread and self.status_subscriber_thread.is_alive():
            self.status_subscriber_thread.join(timeout=5.0)
            if self.status_subscriber_thread.is_alive():
                self.logger.warning("任务状态订阅线程未能正常关闭")
        
        self.logger.info("任务管理器已关闭") 