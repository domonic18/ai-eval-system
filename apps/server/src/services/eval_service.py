from fastapi import Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.eval import Evaluation, EvaluationStatus
from ..schemas.eval import EvaluationResponse, EvaluationStatusResponse
from ..tasks.eval_tasks import run_evaluation
from celery.result import AsyncResult

async def create_evaluation_task(eval_data, db: Session = Depends(get_db)):
    try:
        # 创建评估任务记录
        db_eval = Evaluation(
            task_name=eval_data.task_name,
            model_configuration=eval_data.model_configuration,
            dataset_config=eval_data.dataset_config
        )
        
        db.add(db_eval)
        db.commit()
        db.refresh(db_eval)
        
        try:
            # 添加调试信息
            print(f"正在提交任务，评估ID：{db_eval.id}")
            
            # 启动Celery任务
            from ..tasks.eval_tasks import run_evaluation
            print(f"任务函数: {run_evaluation}")
            print(f"任务函数名称: {run_evaluation.name}")  # 打印任务实际注册的名称
            
            task = run_evaluation.delay(db_eval.id)
            print(f"任务已提交，任务ID: {task.id}")
            
            # 更新任务ID
            db_eval.celery_task_id = task.id
            db.commit()
        except Exception as e:
            # 捕获更详细的错误信息
            import traceback
            print(f"Celery错误: {str(e)}")
            print(traceback.format_exc())
            
            db_eval.status = EvaluationStatus.FAILED
            db_eval.log_output = f"任务队列连接失败: {str(e)}"
            db.commit()
        
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
    except Exception as e:
        print(f"创建评估任务失败: {str(e)}")
        raise e

async def get_evaluation_status(eval_id: int, db: Session = Depends(get_db)):
    # 查询评估任务
    db_eval = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not db_eval:
        return None
    
    # 如果有Celery任务ID，查询任务状态
    if db_eval.celery_task_id:
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
    
    # 没有Celery任务ID
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