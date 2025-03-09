#!/usr/bin/env python3
# 评估任务执行器

import os
# import json
import time
import logging
import threading
import contextlib
from datetime import datetime
# from pathlib import Path
from sqlalchemy.orm import Session
# from typing import Dict, Any, Optional
from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus
from core.config import settings
from tasks.runners.runner import create_runner, get_runner, remove_runner
from utils.redis_manager import RedisManager
from core.config import BASE_DIR
# from tasks.task_eval import update_task_status, update_task_results, update_task_error
# from tasks.task_eval import create_eval_config

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
    """评估任务执行器类"""
    
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
        self.runners = {}
        
    # def handle_task_revoked(self, *args, **kwargs):
    #     """处理任务取消的回调
        
    #     当Celery任务被撤销时调用此方法清理资源
    #     """
    #     logger.info(f"任务[{self.eval_id}]被取消，正在清理资源...")
        
    #     # 终止运行器
    #     runner = get_runner(self.task_id)
    #     if runner:
    #         runner.terminate()
    #         remove_runner(self.task_id)
        
    #     # 更新数据库中的任务状态为CANCELED
    #     try:
    #         with db_session() as db:
    #             from tasks.task_eval import update_task_status
    #             update_task_status(db, self.eval_id, EvaluationStatus.CANCELED)
    #             logger.info(f"已将任务[{self.eval_id}]标记为已取消")
    #     except Exception as e:
    #         logger.error(f"更新取消状态时出错: {str(e)}")
            
    #     # 清理活动任务记录
    #     if self.eval_id in _active_tasks:
    #         del _active_tasks[self.eval_id]
    
    # def monitor_task(self):
    #     """监控评估任务的线程方法
        
    #     监控任务的执行状态，处理任务完成或失败的情况
    #     """
    #     logger.info(f"开始监控任务[{self.eval_id}]")
    #     try:
    #         # 等待任务完成
    #         while self.runner.is_running and not self.runner.is_finished:
    #             time.sleep(5)
                
    #         # 任务已完成，记录最终状态
    #         logger.info(f"任务[{self.eval_id}]监控完成，状态: {'成功' if self.runner.is_successful else '失败'}")
            
    #         # 清理活动任务记录
    #         if self.eval_id in _active_tasks:
    #             del _active_tasks[self.eval_id]
                
    #     except Exception as e:
    #         logger.exception(f"监控任务[{self.eval_id}]时出错: {str(e)}")
            
    #         # 发生异常时尝试更新任务状态
    #         with db_session() as session:
    #             from tasks.task_eval import update_task_error, update_task_status
    #             update_task_error(session, self.eval_id, str(e))
    #             update_task_status(session, self.eval_id, EvaluationStatus.FAILED)
                
    #         # 清理活动任务记录
    #         if self.eval_id in _active_tasks:
    #             del _active_tasks[self.eval_id]
    
    # def start_monitoring(self):
    #     """启动监控线程"""
    #     self.monitor_thread = threading.Thread(target=self.monitor_task, daemon=True)
    #     self.monitor_thread.start()
    
    # def execute(self):

    #     """执行评估任务
        
    #     完整的任务执行流程，包括初始化、运行、监控
        
    #     Returns:
    #         dict: 任务启动状态信息
    #     """
    #     logger.info(f"开始执行评估任务[{self.eval_id}]")
        
    #     # 注册撤销处理
    #     self.celery_task.request.on_revoked = self.handle_task_revoked
        
    #     # 使用数据库会话上下文管理器处理任务启动
    #     with db_session() as db:
    #         # 更新任务状态为运行中
    #         from tasks.task_eval import update_task_status, create_eval_config, update_task_metadata, update_task_error
    #         update_task_status(db, self.eval_id, EvaluationStatus.RUNNING.value)
            
    #         try:
    #             # 读取评估任务
    #             eval_task = db.query(Evaluation).filter(Evaluation.id == self.eval_id).first()
    #             if not eval_task:
    #                 raise ValueError(f"找不到评估任务: {self.eval_id}")
                    
    #             # 创建配置
    #             eval_config = create_eval_config(eval_task)
                
    #             # 清空之前的日志记录
    #             RedisManager.clear_logs(self.eval_id)
                
    #             # 使用上下文管理器创建并管理Runner
    #             runner = create_runner(
    #                 task_id=self.eval_id, 
    #                 working_dir=str(BASE_DIR),
    #                 opencompass_path=settings.opencompass_path
    #             )
    #             self.runner = runner
                
    #             # 将eval_id存入runner的task_id字段以便状态回调使用
    #             self.runner.task_id = self.eval_id
                
    #             # 注册状态更新回调
    #             from tasks.task_eval import handle_task_status_update
    #             self.runner.register_status_callback(handle_task_status_update)
                
    #             # 构建命令
    #             model_name = eval_task.model_name
    #             dataset_name = eval_task.dataset_name
    #             command = self.runner.build_command(model_name, dataset_name, model_args='--debug')
                
    #             # 创建日志文件
    #             logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
    #             os.makedirs(logs_dir, exist_ok=True)
    #             self.log_file = os.path.join(logs_dir, f"eval_{self.eval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
                
    #             # 启动运行器
    #             try:
    #                 runner.run(command, self.log_file)
                    
    #                 # 设置初始任务状态
    #                 self.celery_task.update_state(state='PROGRESS', meta={'progress': 0, 'status': '任务已启动'})
                    
    #                 # 设置任务元数据
    #                 update_task_metadata(db, self.eval_id, {
    #                     'pid': self.runner.process.pid if self.runner.process else None,
    #                     'log_file': self.log_file
    #                 })
                    
    #                 # 将任务记录到活动任务中
    #                 _active_tasks[self.eval_id] = self.runner
                    
    #                 # 启动监控线程
    #                 self.start_monitoring()
                    
    #                 # 返回任务启动成功信息
    #                 return {
    #                     "message": f"评估任务[{self.eval_id}]已启动，正在后台执行",
    #                     "eval_id": self.eval_id,
    #                     "status": "RUNNING"
    #                 }
    #             except Exception as e:
    #                 logger.exception(f"启动评估任务[{self.eval_id}]时出错: {str(e)}")
    #                 error_message = str(e)
    #                 update_task_error(db, self.eval_id, error_message)
    #                 update_task_status(db, self.eval_id, EvaluationStatus.FAILED)
                    
    #                 # 清理资源
    #                 if self.eval_id in _active_tasks:
    #                     del _active_tasks[self.eval_id]
    #                 if get_runner(self.task_id):
    #                     remove_runner(self.task_id)
                    
    #                 raise
                    
    #         except Exception as e:
    #             logger.exception(f"启动评估任务[{self.eval_id}]时出错: {str(e)}")
    #             error_message = str(e)
    #             update_task_error(db, self.eval_id, error_message)
    #             update_task_status(db, self.eval_id, EvaluationStatus.FAILED)
                
    #             # 清理资源
    #             if self.eval_id in _active_tasks:
    #                 del _active_tasks[self.eval_id]
    #             if get_runner(self.task_id):
    #                 remove_runner(self.task_id)
                    
    #             raise 

    def execute_sync(self) -> dict:
        """同步执行评估任务"""
        logger.info(f"开始同步执行评估任务[{self.eval_id}]")
        
        # 使用数据库会话上下文管理器处理任务启动
        with db_session() as db:
            try:
                # 1. 更新任务状态为运行中
                self._update_task_status(db, self.eval_id, EvaluationStatus.RUNNING.value)
                # update_task_status(db, self.eval_id, EvaluationStatus.RUNNING.value)
                
                # 2. 读取评估任务
                eval_task = db.query(Evaluation).filter(Evaluation.id == self.eval_id).first()
                if not eval_task:
                    raise ValueError(f"找不到评估任务: {self.eval_id}")
                    
                # 3. 创建配置
                # eval_config = create_eval_config(eval_task)
                
                # 4. 清空之前的日志记录
                # RedisManager.clear_logs(self.eval_id)
                
                # 5. 创建并配置Runner
                runner = create_runner(
                    eval_id=self.eval_id, 
                    working_dir=str(BASE_DIR),
                    opencompass_path=settings.opencompass_path
                )
                self.runner = runner
                
                
                # 6. 构建命令
                command = self.runner.build_command(eval_task.model_name, 
                                                    eval_task.dataset_name, 
                                                    model_args='--debug')
                
                # 7. 创建日志文件
                self.log_file = self._create_log_file()

                # 8. 同步执行命令
                exit_code = self.runner.run_sync(command, self.log_file)
                
                # 处理执行结果
                if exit_code == 0:
                    final_status = EvaluationStatus.COMPLETED
                    results = self._collect_results()
                else:
                    final_status = EvaluationStatus.FAILED
                    results = {"error": f"非零退出码: {exit_code}"}
                
                # 7. 更新最终状态
                self._update_task_status(db, self.eval_id, final_status.value)
                self._update_task_results(db, self.eval_id, results)
                
                return {
                    "success": exit_code == 0,
                    "exit_code": exit_code,
                    "results": results,
                    "log_path": self.log_file
                }
                
            except Exception as e:
                logger.exception(f"同步执行评估任务[{self.eval_id}]失败: {str(e)}")
                self._update_task_error(db, self.eval_id, str(e))
                self._update_task_status(db, self.eval_id, EvaluationStatus.FAILED.value)
                return {
                    "success": False,
                    "error": str(e),
                    "exit_code": -1
                }

    def _create_log_file(self):
        """创建日志文件"""
        logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
        os.makedirs(logs_dir, exist_ok=True)
        return os.path.join(logs_dir, f"eval_{self.eval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    def _collect_results(self) -> dict:
        """收集任务执行结果"""
        # 从日志文件解析结果
        results = {"output": []}
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    results["output"] = f.readlines()[-100:]  # 获取最后100行日志
        except Exception as e:
            logger.warning(f"收集结果时读取日志失败: {str(e)}")
        
        # 添加其他元数据
        results.update({
            "start_time": self.runner.start_time.isoformat() if self.runner.start_time else None,
            "end_time": datetime.now().isoformat()
            # "duration": self.runner.get_duration() if self.runner else None
        })
        return results
    
    def _update_task_status(self, db: Session, eval_id: int, status: EvaluationStatus, results=None):
        """更新任务状态"""

        # 1. 更新数据库
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if eval_task:
            eval_task.status = status
            if results:
                eval_task.results = results
            db.commit()
        else:
            logger.warning(f"找不到评估任务: {eval_id}")
            return

        # 2. 通过Redis更新任务状态
        try:
            RedisManager.update_task_status(eval_id, {
                "status": status,
                "updated_at": datetime.now().isoformat()
            })
            logger.debug(f"已通过Redis更新任务[{eval_id}]状态: {status}")
        except Exception as e:
            logger.error(f"Redis更新任务状态失败: {str(e)}")

    def _update_task_metadata(self, db: Session, eval_id: int, metadata: dict):
        """更新任务元数据
        
        Args:
            db: 数据库会话
            eval_id: 评估任务ID
            metadata: 元数据字典
        """
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if eval_task:
            # 如果结果字段是None，初始化为空字典
            if eval_task.results is None:
                eval_task.results = {}
            
            # 将元数据添加到结果中
            results = eval_task.results
            
            # 如果没有metadata键，创建一个
            if 'metadata' not in results:
                results['metadata'] = {}
                
            # 更新元数据
            results['metadata'].update(metadata)
            eval_task.results = results
            db.commit()
            logger.info(f"任务[{eval_id}]元数据已更新: {metadata}")

    def _update_task_results(self, db: Session, eval_id: int, results):
        """更新任务结果
        
        Args:
            db: 数据库会话
            eval_id: 评估任务ID
            results: 结果数据
        """
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if eval_task:
            eval_task.results = results
            db.commit()
            logger.info(f"任务[{eval_id}]结果已更新")

    def _update_task_error(self, db: Session, eval_id: int, error_message: str):
        """更新任务错误信息
        
        Args:
            db: 数据库会话
            eval_id: 评估任务ID
            error_message: 错误信息
        """
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if eval_task:
            # 如果结果字段是None，初始化为空字典
            if eval_task.results is None:
                eval_task.results = {}
            
            # 将错误信息添加到结果中
            results = eval_task.results
            results["error"] = error_message
            eval_task.results = results
            db.commit()
            logger.error(f"任务[{eval_id}]出错: {error_message}")
            
            # 同时将错误信息添加到日志中
            self._batch_append_logs(eval_id, [f"错误: {error_message}"])

    def _create_eval_config(self, eval_task):
        """创建评估配置
        
        Args:
            eval_task: 评估任务对象
            
        Returns:
            dict: 评估配置
        """
        config = {
            "model_name": eval_task.model_name,
            "dataset_name": eval_task.dataset_name,
            "model_params": eval_task.model_configuration,
            "dataset_params": eval_task.dataset_configuration
        }
        
        # 添加额外配置
        if hasattr(eval_task, "config_file") and eval_task.config_file:
            config["config_file"] = eval_task.config_file
        
        if hasattr(eval_task, "num_gpus") and eval_task.num_gpus:
            config["num_gpus"] = eval_task.num_gpus
        
        if hasattr(eval_task, "extra_args") and eval_task.extra_args:
            config["extra_args"] = eval_task.extra_args
        
        return config

    def _batch_append_logs(self, eval_id: int, log_lines: list):
        """批量添加任务日志到Redis，避免重复
        
        Args:
            eval_id: 评估任务ID
            log_lines: 新的日志行列表
            redis_client: 可选的Redis客户端实例，如果提供将复用连接
            
        Returns:
            int: 成功添加的日志数量
        """
        if not log_lines:
            return 0
        
        # 过滤掉空行    
        filtered_lines = [line.strip() for line in log_lines if line.strip()]
        if not filtered_lines:
            return 0
            
        try:
            # 使用RedisManager的批量添加方法
            added_count = RedisManager.batch_append_logs(eval_id, filtered_lines)
            if added_count > 0:
                logger.debug(f"任务[{eval_id}]批量添加了{added_count}条日志")
            return added_count
        except Exception as e:
            logger.error(f"批量添加日志出错: {str(e)}")
            return 0
