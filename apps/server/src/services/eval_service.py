from fastapi import Depends
from sqlalchemy.orm import Session
from apps.server.src.db import get_db, SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.schemas.eval import EvaluationResponse, EvaluationStatusResponse
from celery.result import AsyncResult
import traceback
from typing import Optional, Union, Iterator

class EvaluationService:
    """评估服务类，处理评估任务的创建和状态查询"""
    
    def __init__(self):
        """初始化评估服务"""
        pass
    
    async def create_evaluation_task(self, eval_data, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """创建评估任务并启动Celery异步任务
        
        Args:
            eval_data: 评估任务数据
            db: 数据库会话或会话生成器
            
        Returns:
            EvaluationResponse: 评估任务响应对象
        """
        # 处理FastAPI依赖注入的生成器和直接调用的兼容性
        session = None
        should_close_session = False
        
        try:
            # 判断db是生成器还是session对象
            if hasattr(db, 'add'):
                # 已经是session对象
                session = db
            else:
                # 是生成器，获取session对象并标记需要关闭
                try:
                    session = next(db)
                except (TypeError, StopIteration):
                    # 如果不是生成器或者生成器为空，创建新会话
                    session = SessionLocal()
                    should_close_session = True
            
            # 创建评估任务记录
            db_eval = Evaluation(
                task_name=eval_data.task_name,
                model_configuration=eval_data.model_configuration,
                dataset_config=eval_data.dataset_config
            )
            
            session.add(db_eval)
            session.commit()
            session.refresh(db_eval)
            
            try:
                # 添加调试信息
                print(f"正在提交任务，评估ID：{db_eval.id}")
                
                # 启动Celery任务
                from apps.server.src.tasks.eval_tasks import run_evaluation
                print(f"任务函数: {run_evaluation}")
                print(f"任务函数名称: {run_evaluation.name}")  # 打印任务实际注册的名称
                
                task = run_evaluation.delay(db_eval.id)
                print(f"任务已提交，任务ID: {task.id}")
                
                # 更新任务ID
                db_eval.celery_task_id = task.id
                session.commit()
            except Exception as e:
                # 捕获更详细的错误信息
                print(f"Celery错误: {str(e)}")
                print(traceback.format_exc())
                
                db_eval.status = EvaluationStatus.FAILED
                db_eval.log_output = f"任务队列连接失败: {str(e)}"
                session.commit()
            
            return self._create_evaluation_response(db_eval)
        except Exception as e:
            print(f"创建评估任务失败: {str(e)}")
            traceback.print_exc()
            raise e
        finally:
            # 如果我们创建了新会话，需要关闭它
            if should_close_session and session:
                session.close()

    async def get_evaluation_status(self, eval_id: int, db: Session = Depends(get_db)) -> Optional[EvaluationStatusResponse]:
        """获取评估任务状态
        
        Args:
            eval_id: 评估ID
            db: 数据库会话
            
        Returns:
            EvaluationStatusResponse: 评估任务状态响应对象，如果任务不存在则返回None
        """
        # 查询评估任务
        db_eval = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not db_eval:
            return None
        
        # 如果有Celery任务ID，查询任务状态
        if db_eval.celery_task_id:
            return self._create_evaluation_status_with_celery(db_eval)
        
        # 没有Celery任务ID
        return self._create_evaluation_status_without_celery(db_eval)
    
    def _create_evaluation_response(self, db_eval: Evaluation) -> EvaluationResponse:
        """从数据库模型创建评估响应对象
        
        Args:
            db_eval: 数据库评估模型
            
        Returns:
            EvaluationResponse: 评估响应对象
        """
        return EvaluationResponse(
            id=db_eval.id,
            task_name=db_eval.task_name,
            model_configuration=db_eval.model_configuration,
            dataset_config=db_eval.dataset_config,
            status=db_eval.status.value,
            celery_task_id=db_eval.celery_task_id,
            created_at=db_eval.created_at,
            updated_at=db_eval.updated_at
        )
    
    def _create_evaluation_status_with_celery(self, db_eval: Evaluation) -> EvaluationStatusResponse:
        """创建包含Celery任务状态的评估状态响应
        
        Args:
            db_eval: 数据库评估模型
            
        Returns:
            EvaluationStatusResponse: 评估状态响应对象
        """
        task_result = AsyncResult(db_eval.celery_task_id)
        task_status = task_result.status
        task_info = task_result.info if task_result.info else {}
        
        # 构建详细响应
        return EvaluationStatusResponse(
            id=db_eval.id,
            task_name=db_eval.task_name,
            status=db_eval.status.value,
            celery_status=task_status,
            progress=task_info.get('progress', 0) if isinstance(task_info, dict) else 0,
            message=task_info.get('status', '') if isinstance(task_info, dict) else '',
            log_output=db_eval.log_output,
            results=db_eval.results,
            created_at=db_eval.created_at,
            updated_at=db_eval.updated_at
        )
    
    def _create_evaluation_status_without_celery(self, db_eval: Evaluation) -> EvaluationStatusResponse:
        """创建不包含Celery任务状态的评估状态响应
        
        Args:
            db_eval: 数据库评估模型
            
        Returns:
            EvaluationStatusResponse: 评估状态响应对象
        """
        return EvaluationStatusResponse(
            id=db_eval.id,
            task_name=db_eval.task_name,
            status=db_eval.status.value,
            celery_status=None,
            progress=0,
            message='',
            log_output=db_eval.log_output,
            results=db_eval.results,
            created_at=db_eval.created_at,
            updated_at=db_eval.updated_at
        )

# 创建服务实例
evaluation_service = EvaluationService()

# 为了向后兼容，保留原来的函数
async def create_evaluation_task(eval_data, db: Union[Session, Iterator[Session]] = Depends(get_db)):
    return await evaluation_service.create_evaluation_task(eval_data, db)

async def get_evaluation_status(eval_id: int, db: Session = Depends(get_db)):
    return await evaluation_service.get_evaluation_status(eval_id, db) 