#!/usr/bin/env python3
# 评估任务执行器

import os
import json
import time
import logging
import threading
import contextlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus
from core.config import OPENCOMPASS_PATH
from tasks.runners.runner_opencompas import OpenCompassRunner, create_runner, get_runner, remove_runner
from utils.redis_manager import RedisManager

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

# 配置日志
logger = logging.getLogger("eval_tasks")

# 跟踪活动的任务字典
_active_tasks = {}

@contextlib.contextmanager
def db_session():
    """数据库会话上下文管理器
    
    使用示例:
    with db_session() as db:
        # 使用数据库会话db
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

class TaskEvaluator:
    """评估任务执行器类
    
    封装了评估任务的执行、监控和资源管理逻辑
    """
    
    def __init__(self, celery_task, eval_id):
        """初始化评估任务执行器
        
        Args:
            celery_task: Celery任务实例
            eval_id: 评估任务ID
        """
        self.celery_task = celery_task
        self.eval_id = eval_id
        self.task_id = f"eval_{eval_id}"
        self.runner = None
        self.monitor_thread = None
        self.log_file = None
        
    def handle_task_revoked(self, *args, **kwargs):
        """处理任务取消的回调
        
        当Celery任务被撤销时调用此方法清理资源
        """
        logger.info(f"任务[{self.eval_id}]被取消，正在清理资源...")
        
        # 终止运行器
        runner = get_runner(self.task_id)
        if runner:
            runner.terminate()
            remove_runner(self.task_id)
        
        # 更新数据库中的任务状态为CANCELED
        try:
            with db_session() as db:
                from tasks.task_eval import update_task_status
                update_task_status(db, self.eval_id, EvaluationStatus.CANCELED)
                logger.info(f"已将任务[{self.eval_id}]标记为已取消")
        except Exception as e:
            logger.error(f"更新取消状态时出错: {str(e)}")
            
        # 清理活动任务记录
        if self.eval_id in _active_tasks:
            del _active_tasks[self.eval_id]
    
    def monitor_task(self):
        """监控评估任务的线程方法
        
        监控任务的执行状态，处理任务完成或失败的情况
        """
        logger.info(f"开始监控任务[{self.eval_id}]")
        try:
            # 等待任务完成
            while self.runner.is_running and not self.runner.is_finished:
                time.sleep(5)
                
            # 任务已完成，记录最终状态
            logger.info(f"任务[{self.eval_id}]监控完成，状态: {'成功' if self.runner.is_successful else '失败'}")
            
            # 清理活动任务记录
            if self.eval_id in _active_tasks:
                del _active_tasks[self.eval_id]
                
        except Exception as e:
            logger.exception(f"监控任务[{self.eval_id}]时出错: {str(e)}")
            
            # 发生异常时尝试更新任务状态
            with db_session() as session:
                from tasks.task_eval import update_task_error, update_task_status
                update_task_error(session, self.eval_id, str(e))
                update_task_status(session, self.eval_id, EvaluationStatus.FAILED)
                
            # 清理活动任务记录
            if self.eval_id in _active_tasks:
                del _active_tasks[self.eval_id]
    
    def start_monitoring(self):
        """启动监控线程"""
        self.monitor_thread = threading.Thread(target=self.monitor_task, daemon=True)
        self.monitor_thread.start()
    
    def execute(self):
        """执行评估任务
        
        完整的任务执行流程，包括初始化、运行、监控
        
        Returns:
            dict: 任务启动状态信息
        """
        logger.info(f"开始执行评估任务[{self.eval_id}]")
        
        # 注册撤销处理
        self.celery_task.request.on_revoked = self.handle_task_revoked
        
        # 使用数据库会话上下文管理器处理任务启动
        with db_session() as db:
            # 更新任务状态为运行中
            from tasks.task_eval import update_task_status, create_eval_config, update_task_metadata, update_task_error
            update_task_status(db, self.eval_id, EvaluationStatus.RUNNING)
            
            try:
                # 读取评估任务
                eval_task = db.query(Evaluation).filter(Evaluation.id == self.eval_id).first()
                if not eval_task:
                    raise ValueError(f"找不到评估任务: {self.eval_id}")
                    
                # 创建配置
                eval_config = create_eval_config(eval_task)
                
                # 清空之前的日志记录
                RedisManager.clear_logs(self.eval_id)
                
                # 使用上下文管理器创建并管理Runner
                runner = create_runner(
                    task_id=self.task_id, 
                    working_dir=str(BASE_DIR),
                    opencompass_path=OPENCOMPASS_PATH
                )
                self.runner = runner
                
                # 将eval_id存入runner的task_id字段以便状态回调使用
                self.runner.task_id = self.eval_id
                
                # 注册状态更新回调
                from tasks.task_eval import handle_task_status_update
                self.runner.register_status_callback(handle_task_status_update)
                
                # 构建命令
                model_name = eval_task.model_name
                dataset_name = eval_task.dataset_name
                command = self.runner.build_command(model_name, dataset_name, model_args='--debug')
                
                # 创建日志文件
                logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
                os.makedirs(logs_dir, exist_ok=True)
                self.log_file = os.path.join(logs_dir, f"eval_{self.eval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                
                # 启动运行器
                try:
                    runner.run(command, self.log_file)
                    
                    # 设置初始任务状态
                    self.celery_task.update_state(state='PROGRESS', meta={'progress': 0, 'status': '任务已启动'})
                    
                    # 设置任务元数据
                    update_task_metadata(db, self.eval_id, {
                        'pid': self.runner.process.pid if self.runner.process else None,
                        'log_file': self.log_file
                    })
                    
                    # 将任务记录到活动任务中
                    _active_tasks[self.eval_id] = self.runner
                    
                    # 启动监控线程
                    self.start_monitoring()
                    
                    # 返回任务启动成功信息
                    return {
                        "message": f"评估任务[{self.eval_id}]已启动，正在后台执行",
                        "eval_id": self.eval_id,
                        "status": "RUNNING"
                    }
                except Exception as e:
                    logger.exception(f"启动评估任务[{self.eval_id}]时出错: {str(e)}")
                    error_message = str(e)
                    update_task_error(db, self.eval_id, error_message)
                    update_task_status(db, self.eval_id, EvaluationStatus.FAILED)
                    
                    # 清理资源
                    if self.eval_id in _active_tasks:
                        del _active_tasks[self.eval_id]
                    if get_runner(self.task_id):
                        remove_runner(self.task_id)
                    
                    raise
                    
            except Exception as e:
                logger.exception(f"启动评估任务[{self.eval_id}]时出错: {str(e)}")
                error_message = str(e)
                update_task_error(db, self.eval_id, error_message)
                update_task_status(db, self.eval_id, EvaluationStatus.FAILED)
                
                # 清理资源
                if self.eval_id in _active_tasks:
                    del _active_tasks[self.eval_id]
                if get_runner(self.task_id):
                    remove_runner(self.task_id)
                    
                raise 