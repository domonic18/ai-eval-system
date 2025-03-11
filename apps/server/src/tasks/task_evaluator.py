#!/usr/bin/env python3
# 评估任务执行器

import os
import logging
import contextlib
from datetime import datetime
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus
from core.config import settings
from tasks.runners.runner_base import create_runner, get_runner, remove_runner
from utils.redis_manager import RedisManager
from core.config import BASE_DIR
from tasks.runners.runner_enhanced import EnhancedRunner
from pathlib import Path
from services.evaluation.result_collector import ResultCollector


# 配置日志
logger = logging.getLogger("eval_tasks")

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
        self.runner = None
        self.monitor_thread = None
        self.log_file = None
        self.runners = {}
    

    def execute_sync(self) -> dict:
        """同步执行评估任务"""
        logger.info(f"开始同步执行评估任务[{self.eval_id}]")
        
        # 使用数据库会话上下文管理器处理任务启动
        with db_session() as db:
            try:
                # 1. 更新任务状态为运行中
                self._update_task_status(db, self.eval_id, EvaluationStatus.RUNNING.value)
                
                # 2. 读取评估任务
                eval_task = db.query(Evaluation).filter(Evaluation.id == self.eval_id).first()
                if not eval_task:
                    raise ValueError(f"找不到评估任务: {self.eval_id}")
                    
                # 3. 初始化增强型执行器
                runner = EnhancedRunner(
                    eval_id=self.eval_id,
                    working_dir=Path(BASE_DIR),
                    opencompass_path=settings.opencompass_path
                )
                work_dir = Path(BASE_DIR) / "logs" / f"eval_{self.eval_id}"
                
                # 2. 配置环境变量
                # runner.env_manager.load_env_json(eval_task.eval_config)
                
                # 7. 创建日志文件
                self.log_file = self._create_log_file()

                # 3. 执行任务
                exit_code = runner.execute(eval_task)
                
                # 4. 收集结果
                # collector = ResultCollector(self.eval_id, work_dir)
                # collector.collect_results()
                
                # 5. 结果处理
                if exit_code == 0:
                    final_status = EvaluationStatus.COMPLETED
                    # 收集结果
                    collector = ResultCollector(self.eval_id, work_dir)
                    results = collector.collect_results()
                    # results = self._collect_results()
                    # self._save_to_database(results)
                else:
                    final_status = EvaluationStatus.FAILED
                    results = {"error": f"非零退出码: {exit_code}"}

                
                # 5. 清空之前的日志记录
                # RedisManager.clear_logs(self.eval_id)
                
                # # 5. 创建并配置Runner
                # runner = create_runner(
                #     eval_id=self.eval_id, 
                #     working_dir=str(BASE_DIR),
                #     opencompass_path=settings.opencompass_path
                # )
                # self.runner = runner
                
                
                # # 6. 构建命令
                # command = self.runner.build_command(eval_task.model_name, 
                #                                     eval_task.dataset_name, 
                #                                     model_args='--debug')
                
                # # 7. 创建日志文件
                # self.log_file = self._create_log_file()

                # # 8. 同步执行命令
                # exit_code = self.runner.run_sync(command, self.log_file)
                
                # # 结果处理
                # if exit_code == 0:
                #     final_status = EvaluationStatus.COMPLETED
                #     results = self._collect_results()
                #     self._save_to_database(results)
                # else:
                #     final_status = EvaluationStatus.FAILED
                #     results = {"error": f"非零退出码: {exit_code}"}
                
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
