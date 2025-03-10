import logging
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from celery.result import AsyncResult
from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus
from tasks.task_eval import run_evaluation
from tasks.runners.runner_base import get_runner
from utils.redis_manager import RedisManager
import psutil


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
                "eval_status": evaluation.status,  # 数据库状态
                "success": "true",
                "return_code": 0
            }
        except Exception as e:
            return {"error": str(e)}

    def terminate_task(self, eval_id: int) -> dict:
        """使用Celery原生终止功能"""
        try:
            # 获取数据库中的任务记录
            evaluation = self._get_db_evaluation(eval_id)
            if not evaluation or not evaluation.task_id:
                return {"success": False, "message": "任务不存在"}

            # 获取Celery任务实例
            task = AsyncResult(evaluation.task_id)
            
            # 双重检查任务状态
            if task.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                return {"success": False, "message": "任务已处于最终状态无法终止"}

            try:
                task.revoke(terminate=True, signal='SIGTERM', timeout=10)
                # 如果5秒后仍在运行，强制终止
                if not task.ready():
                    task.revoke(terminate=True, signal='SIGKILL')
                    logger.warning(f"强制终止任务 {evaluation.task_id}")

                # 清理子进程（关键修复点）
                self._cleanup_child_processes(eval_id)
                
                return {"success": True, "message": "任务终止指令已发送"}
            except Exception as e:
                logger.error(f"终止任务异常: {str(e)}")
                return {"success": False, "message": f"终止失败: {str(e)}"}
        except Exception as e:
            logger.exception("终止任务时发生意外错误")
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
            return db.query(Evaluation).get(eval_id)
    