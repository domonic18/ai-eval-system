from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from apps.server.src.db import get_db, SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from celery.result import AsyncResult
import traceback
from typing import Optional, Union, Iterator, Dict, Any
import logging
import json
from pathlib import Path
from apps.server.src.tasks.eval_tasks import run_evaluation

# 日志配置
logger = logging.getLogger(__name__)

class EvaluationService:
    """评估服务类，处理评估任务的创建和状态查询"""
    
    def __init__(self):
        """初始化评估服务"""
        pass
    
    async def create_evaluation_task(self, eval_data: EvaluationCreate, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """创建评估任务并启动异步任务
        
        Args:
            eval_data: 评估数据
            db: 数据库会话（可能是 Session 对象或 FastAPI 依赖的生成器）
            
        Returns:
            EvaluationResponse: 评估响应
        """
        # 处理 db 可能是生成器的情况（FastAPI 依赖注入）
        close_db = False
        try:
            if hasattr(db, "__next__"):
                # db 是一个生成器（来自 FastAPI 的 Depends）
                db_session = next(db)
            else:
                # db 是直接传入的 Session 对象
                db_session = db
        except Exception:
            # 如果出错，创建一个新的会话
            logger.warning("提供的数据库会话无效，创建新会话")
            db_session = SessionLocal()
            close_db = True
        
        try:
            # 创建新的评估记录
            model_configuration = {}
            dataset_configuration = {}
            
            # 如果提供了模型配置，解析它
            if eval_data.model_configuration:
                try:
                    if isinstance(eval_data.model_configuration, str):
                        model_configuration = json.loads(eval_data.model_configuration)
                    else:
                        model_configuration = eval_data.model_configuration
                except json.JSONDecodeError:
                    model_configuration = {"config_error": "无效的 JSON 格式"}
            
            # 如果提供了数据集配置，解析它
            if eval_data.dataset_configuration:
                try:
                    if isinstance(eval_data.dataset_configuration, str):
                        dataset_configuration = json.loads(eval_data.dataset_configuration)
                    else:
                        dataset_configuration = eval_data.dataset_configuration
                except json.JSONDecodeError:
                    dataset_configuration = {"config_error": "无效的 JSON 格式"}

            # 创建评估记录
            db_eval = Evaluation(
                model_name=eval_data.model_name,
                dataset_name=eval_data.dataset_name,
                model_configuration=model_configuration,
                dataset_configuration=dataset_configuration,
                eval_config=eval_data.eval_config or {},
                status=EvaluationStatus.PENDING.value,
                log_dir=""
            )
            
            # 添加并提交
            db_session.add(db_eval)
            db_session.commit()
            db_session.refresh(db_eval)
            
            # 创建日志目录
            log_dir = Path(f"logs/eval_{db_eval.id}")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 更新日志目录
            db_eval.log_dir = str(log_dir)
            db_session.commit()
            
            # 启动 Celery 任务
            try:
                task = run_evaluation.delay(db_eval.id)
                logger.info(f"启动评估任务 {db_eval.id}，Celery 任务 ID: {task.id}")
                
                # 更新任务ID
                db_eval.task_id = task.id
                db_session.commit()
                
                # 构建响应
                return EvaluationResponse(
                    id=db_eval.id,
                    model_name=db_eval.model_name,
                    dataset_name=db_eval.dataset_name,
                    status=db_eval.status,
                    created_at=db_eval.created_at,
                    updated_at=db_eval.updated_at,
                    task_id=task.id
                )
            except Exception as e:
                # 记录 Celery 任务创建失败的详细信息
                error_detail = traceback.format_exc()
                logger.error(f"创建 Celery 任务失败: {str(e)}")
                logger.error(error_detail)
                
                # 更新评估状态为失败
                db_eval.status = EvaluationStatus.FAILED.value
                db_eval.error_message = f"启动评估任务失败: {str(e)}"
                db_session.commit()
                
                # 重新抛出异常
                raise Exception(f"启动评估任务失败: {str(e)}")
                
        except SQLAlchemyError as e:
            # 回滚事务
            db_session.rollback()
            error_msg = f"数据库错误: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise Exception(error_msg)
        
        except Exception as e:
            # 处理其他异常
            error_msg = f"创建评估任务时出错: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            raise Exception(error_msg)
        
        finally:
            # 如果我们创建了新的会话，关闭它
            if close_db:
                db_session.close()

    async def get_evaluation_status(self, eval_id: int, db: Session = Depends(get_db)) -> Optional[EvaluationStatusResponse]:
        """获取评估任务状态
        
        Args:
            eval_id: 评估ID
            db: 数据库会话
            
        Returns:
            EvaluationStatusResponse: 评估任务状态响应对象，如果任务不存在则返回None
        """
        eval_record = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not eval_record:
            return None
        
        # 如果任务正在运行，尝试获取当前进度
        progress_info = {}
        if eval_record.status == EvaluationStatus.RUNNING.value and eval_record.task_id:
            try:
                # 尝试从 Celery 获取任务状态
                task = run_evaluation.AsyncResult(eval_record.task_id)
                if task.state == 'PROGRESS' and task.info:
                    progress_info = task.info
                
                # 如果任务已完成但状态未更新，更新状态
                if task.state == 'SUCCESS' and eval_record.status != EvaluationStatus.COMPLETED.value:
                    eval_record.status = EvaluationStatus.COMPLETED.value
                    db.commit()
                elif task.state == 'FAILURE' and eval_record.status != EvaluationStatus.FAILED.value:
                    eval_record.status = EvaluationStatus.FAILED.value
                    eval_record.error_message = str(task.result) if task.result else "任务失败，无错误详情"
                    db.commit()
            except Exception as e:
                logger.warning(f"获取任务 {eval_record.task_id} 状态时出错: {str(e)}")
        
        # 构建响应
        response = EvaluationStatusResponse(
            id=eval_record.id,
            model_name=eval_record.model_name,
            dataset_name=eval_record.dataset_name,
            status=eval_record.status,
            created_at=eval_record.created_at,
            updated_at=eval_record.updated_at,
            task_id=eval_record.task_id,
            error_message=eval_record.error_message,
            results=eval_record.results,
            progress=progress_info.get('progress', 0) if progress_info else 0,
            details=progress_info.get('details', {}) if progress_info else {}
        )
        
        return response

    def get_opencompass_config(self, model_name: str, dataset_name: str, 
                              model_configuration: Dict[str, Any], 
                              dataset_configuration: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建 OpenCompass 配置
        
        Args:
            model_name: 模型名称
            dataset_name: 数据集名称
            model_configuration: 模型配置
            dataset_configuration: 数据集配置
        
        Returns:
            Dict[str, Any]: OpenCompass 配置
        """
        # 基础配置
        config = {
            "model": {
                "name": model_name,
                "path": model_configuration.get("path", ""),
                "type": model_configuration.get("type", "huggingface"),
            },
            "dataset": {
                "name": dataset_name,
                "path": dataset_configuration.get("path", ""),
            },
            "output_path": model_configuration.get("output_path", "outputs/default"),
        }
        
        # 添加其他模型配置
        if "api_key" in model_configuration:
            config["model"]["api_key"] = model_configuration["api_key"]
        
        if "api_base" in model_configuration:
            config["model"]["api_base"] = model_configuration["api_base"]
        
        if "parameters" in model_configuration:
            config["model"]["parameters"] = model_configuration["parameters"]
        
        # 添加数据集特定配置
        if "subset" in dataset_configuration:
            config["dataset"]["subset"] = dataset_configuration["subset"]
        
        if "split" in dataset_configuration:
            config["dataset"]["split"] = dataset_configuration["split"]
        
        return config

# 创建服务实例
evaluation_service = EvaluationService()

# 为了向后兼容，保留原来的函数
async def create_evaluation_task(eval_data, db: Union[Session, Iterator[Session]] = Depends(get_db)):
    return await evaluation_service.create_evaluation_task(eval_data, db)

async def get_evaluation_status(eval_id: int, db: Session = Depends(get_db)):
    return await evaluation_service.get_evaluation_status(eval_id, db) 