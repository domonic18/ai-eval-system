import logging
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from celery.result import AsyncResult
from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus
from tasks.task_eval import run_evaluation
from tasks.runners.runner_base import get_runner
from utils.redis_manager import RedisManager
import psutil
import sqlalchemy.exc
from core.repositories import EvaluationRepository
from utils.utils_db import db_operation
import time


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
        """创建并启动Celery任务
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 任务创建结果
        """
        try:
            # 使用同步方式获取评估记录
            eval_data = EvaluationRepository.get_evaluation_by_id(db, eval_id)
            if not eval_data:
                return {
                    "success": False,
                    "message": f"未找到ID为 {eval_id} 的评估任务"
                }
            
            # 创建Celery任务
            task = run_evaluation.apply_async(
                args=(eval_id,),
                queue='eval_tasks',  # 显式指定队列
                priority=0,
                serializer='json'
                # 添加以下参数确保严格顺序
                # ignore_result=False,
                # acks_late=True,
                # track_started=True
            )

            # 更新数据库中的任务ID
            with db_operation(db) as session:
                eval_record = session.query(Evaluation).filter(Evaluation.id == eval_id).first()
                if eval_record:
                    eval_record.task_id = task.id
                    session.commit()
            
            return {
                "success": True,
                "task_id": task.id,
                "message": "任务已创建并开始执行"
            }
        except Exception as e:
            logger.error(f"创建任务失败 [eval_id={eval_id}]: {str(e)}")
            return {
                "success": False,
                "message": f"创建任务失败: {str(e)}"
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
                "eval_status": evaluation.status,  # 数据库状态
                "success": "true",
                "return_code": 0
            }
        except Exception as e:
            return {"error": str(e)}

    def terminate_task(self, eval_id: int) -> dict:
        """使用Celery原生终止功能"""
        try:
            with SessionLocal() as db:  # 使用上下文管理器管理会话
                # 获取最小必要字段
                evaluation = db.query(
                    Evaluation.id,
                    Evaluation.task_id,
                    Evaluation.status
                ).filter(Evaluation.id == eval_id).first()

                if not evaluation or not evaluation.task_id:
                    return {"success": False, "message": "任务不存在"}

                try:
                    # 首先在Redis中设置终止标志
                    RedisManager.update_task_status(eval_id, {
                        "terminate_flag": True,
                        "timestamp": time.time()
                    })
                    logger.info(f"已在Redis中设置任务 {eval_id} 的终止标志")
                    
                    task = AsyncResult(evaluation.task_id)
                    
                    # 现有的检查方法存在问题，采用更安全的方式检查任务状态
                    # 移除对task.state的直接访问，使用数据库中的状态替代
                    db_status = evaluation.status.upper() if evaluation.status else "UNKNOWN"
                    
                    # 如果数据库状态表明任务已完成或失败，则不允许终止
                    if db_status in ['COMPLETED', 'FAILED', 'TERMINATED']:
                        return {"success": False, "message": "任务已处于最终状态无法终止"}
                    
                    # 直接尝试中止任务，不再检查任务状态
                    logger.info(f"尝试终止任务 {evaluation.task_id}")
                    
                    # 使用Redis终止标志通知运行中的任务
                    # 任务会在下一次循环中检查此标志并自行终止
                    
                    # 为确保安全，仍然发送信号尝试终止
                    try:
                        # 先尝试温和地终止
                        task.revoke(terminate=True, signal='SIGTERM', timeout=10)
                    except Exception as e:
                        logger.warning(f"发送SIGTERM信号失败: {str(e)}")
                    
                    # 清理子进程（关键修复点）
                    self._cleanup_child_processes(eval_id)
                    
                    # 更新数据库状态
                    db_eval = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                    if db_eval:
                        db_eval.status = EvaluationStatus.TERMINATED.value
                        db.commit()
                    
                    return {"success": True, "message": "任务终止指令已发送"}
                    
                except Exception as e:
                    logger.error(f"终止过程异常: {str(e)}")
                    return {"success": False, "message": f"终止任务时发生错误: {str(e)}"}
                
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(f"数据库操作失败: {str(e)}")
            return {"success": False, "message": "数据库服务异常"}
        except Exception as e:
            logger.exception("系统级错误")
            return {"success": False, "message": "内部服务错误"}

    def _cleanup_child_processes(self, task_id: str):
        """清理子进程"""
        try:
            # 获取运行器实例
            runner = get_runner(task_id)
            if runner and runner.process:
                # 终止进程树
                parent = psutil.Process(runner.process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                parent.kill()
                logger.info(f"已清理任务 {task_id} 的 {len(children)+1} 个进程")
        except Exception as e:
            logger.warning(f"清理子进程失败: {str(e)}")

    def _get_db_evaluation(self, eval_id: int):
        """辅助方法获取数据库记录"""
        with SessionLocal() as db:
            # 使用with语句自动管理会话生命周期
            # 显式加载需要的字段，避免延迟加载
            return db.query(
                Evaluation.id,
                Evaluation.task_id,
                Evaluation.status
            ).filter(Evaluation.id == eval_id).first()
    