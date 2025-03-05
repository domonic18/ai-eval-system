"""任务管理器

管理任务的创建、执行、状态追踪和终止。
实现任务队列和并发控制。
"""

import os
import time
import logging
import threading
import queue
from typing import Dict, List, Optional, Any, Tuple, Deque
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from collections import deque

from sqlalchemy.orm import Session
from celery.result import AsyncResult

from apps.server.src.db import SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.celery_app import celery_app
from apps.server.src.tasks.eval_tasks import run_evaluation
from apps.server.src.tasks.opencompass_runner import get_runner
from apps.server.src.utils.redis_manager import RedisManager
from apps.server.src.tasks.celery_tasks import execute_evaluation_task

# 配置日志
logger = logging.getLogger(__name__)

# 任务状态枚举
class TaskStatus(Enum):
    PENDING = auto()      # 等待中（新创建）
    WAITING = auto()      # 等待队列中
    QUEUED = auto()       # 已加入Celery队列
    RUNNING = auto()      # 正在运行
    COMPLETED = auto()    # 已完成
    FAILED = auto()       # 失败
    TERMINATED = auto()   # 被终止
    
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


# 使用单例模式实现全局任务管理器
class TaskManager:
    """任务管理器类
    
    管理所有任务的创建、执行和状态追踪
    实现任务队列和并发控制
    集成Celery分布式任务执行
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式实现"""
        with cls._lock:
            if cls._instance is None:
                instance = super(TaskManager, cls).__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance
    
    def __init__(self):
        """初始化任务管理器"""
        # 避免重复初始化
        if self._initialized:
            return
            
        # 任务管理数据结构
        self.tasks = {}                  # 评估ID -> 任务信息的映射
        self.celery_tasks = {}           # Celery任务ID -> 评估ID的映射
        self.active_tasks = set()        # 当前活动任务的评估ID集合
        self.waiting_queue = deque()     # 等待执行的任务队列（评估ID）
        self.max_concurrent_tasks = 2    # 最大并发任务数
        
        # 线程安全锁
        self.task_lock = threading.RLock()
        
        # 调度器锁
        self.scheduler_lock = threading.RLock()
        
        # Redis管理器
        self.redis_manager = RedisManager()
        
        # 初始化完成标记
        self._initialized = True
        
        logger.info("任务管理器初始化完成")
    
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
        with self.scheduler_lock:
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
        
        Args:
            eval_id: 评估ID
            status: 新状态
            metadata: 可选的元数据
            
        Returns:
            bool: 是否成功更新
        """
        with self.task_lock:
            # 检查任务是否存在
            if eval_id not in self.tasks:
                logger.warning(f"任务不存在，无法更新状态 [eval_id={eval_id}]")
                return False
            
            task_info = self.tasks[eval_id]
            old_status = task_info["status"]
            
            # 更新任务状态
            task_info["status"] = status
            task_info["updated_at"] = datetime.now()
            
            # 更新元数据
            if metadata:
                for key, value in metadata.items():
                    task_info[key] = value
            
            # 处理任务状态变更
            if old_status != status:
                # 处理任务开始运行
                if status == TaskStatus.RUNNING:
                    # 确保任务在活动集合中
                    if eval_id not in self.active_tasks:
                        self.active_tasks.add(eval_id)
                    logger.info(f"任务开始运行 [eval_id={eval_id}], 当前活动任务数: {len(self.active_tasks)}/{self.max_concurrent_tasks}")
                
                # 处理任务结束
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TERMINATED]:
                    # 如果任务结束，从活动集合中移除
                    if eval_id in self.active_tasks:
                        self.active_tasks.remove(eval_id)
                        logger.info(f"任务已结束 [eval_id={eval_id}, status={status}], 当前活动任务数: {len(self.active_tasks)}/{self.max_concurrent_tasks}")
                        
                        # 调度下一个任务
                        with SessionLocal() as db:
                            self._schedule_next_task(db)
            
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
    
    def clean_tasks(self, max_age_hours: int = 24) -> int:
        """清理旧任务
        
        Args:
            max_age_hours: 最大任务保留时间（小时）
            
        Returns:
            int: 清理的任务数量
        """
        with self.task_lock:
            now = datetime.now()
            to_remove = []
            
            for eval_id, task_info in self.tasks.items():
                # 只清理已完成、失败或终止的任务
                if task_info["status"] not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TERMINATED]:
                    continue
                
                # 检查任务年龄
                age = (now - task_info["updated_at"]).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(eval_id)
                    
                    # 清理Celery任务映射
                    celery_id = task_info.get("celery_id")
                    if celery_id and celery_id in self.celery_tasks:
                        del self.celery_tasks[celery_id]
            
            # 移除过期任务
            for eval_id in to_remove:
                # 确保不在活动任务和等待队列中
                if eval_id in self.active_tasks:
                    self.active_tasks.remove(eval_id)
                try:
                    self.waiting_queue.remove(eval_id)
                except ValueError:
                    pass
                
                # 删除任务
                del self.tasks[eval_id]
                
            return len(to_remove) 