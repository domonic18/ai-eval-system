import logging
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends
from fastapi import HTTPException, status
from typing import Optional, Union, Iterator, Dict, Any, List
from models.eval import Evaluation, EvaluationStatus
from schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from api.deps import get_db
from utils.utils_db import async_db_operation,db_operation
from tasks.task_manager import TaskManager
from core.repositories.evaluation_repository import EvaluationRepository
from utils.redis_manager import RedisManager
from tasks.runners.runner_base import get_runner
import os
from pathlib import Path
from core.config import settings
from sqlalchemy import select, func, or_, desc, String, cast
from sqlalchemy.orm import joinedload



# 日志配置
logger = logging.getLogger(__name__)

class EvaluationService:
    """评估服务类，处理评估任务的创建和状态查询"""
    
    def __init__(self):
        """初始化评估服务"""
        self.task_manager = TaskManager()
    
    async def create_evaluation_task(self, eval_data: EvaluationCreate, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """创建评估任务
        
        使用TaskManager创建并管理评估任务，支持队列和并发控制
        
        Args:
            eval_data: 评估数据
            db: 数据库会话
            
        Returns:
            dict: 创建结果
        """
        
        # 特殊处理逻辑：
        if eval_data.api_type == "dify":
            eval_data.env_vars = self.adapt_dify_configuration(
                env_vars=eval_data.env_vars,
                dify2openai_url=settings.dify2openai_url
            )

        # 确保有用户ID
        if not eval_data.user_id:
            # 如果没有提供用户ID，使用默认用户ID（应该避免这种情况）
            eval_data.user_id = 1  # 默认系统用户ID
        
        # 创建评估记录
        db_eval = await EvaluationRepository.create_evaluation_async(
            db,
            model_name=eval_data.model_name,
            dataset_names=eval_data.datasets.names,
            model_configuration=eval_data.model_configuration,
            dataset_configuration=eval_data.datasets.configuration,
            eval_config=eval_data.eval_config,
            env_vars=eval_data.env_vars,
            user_id=eval_data.user_id  # 添加用户ID
        )
                
        # 使用TaskManager创建任务
        task_result = self.task_manager.create_task(db_eval.id, db)
        
        if not task_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=task_result["message"]
            )
        
        return EvaluationResponse(
            id=db_eval.id,
            model_name=db_eval.model_name,
            dataset_names=db_eval.dataset_names,
            status=db_eval.status,
            created_at=db_eval.created_at,
            updated_at=db_eval.updated_at,
            task_id=task_result["task_id"]
        )


    def get_evaluation_status(self, eval_id: int, db: Session):
        """获取评估任务状态
        
        优先使用TaskManager获取任务状态，如果失败则回退到数据库查询
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Optional[EvaluationStatusResponse]: 评估任务状态
        """
        # 1. 从TaskManager获取任务状态
        try:
            # 首先尝试使用TaskManager获取任务状态
            task_status = self.task_manager.get_task_status(eval_id)
            
            if task_status.get("success", False):
                # 从TaskManager获取状态成功
                status_info = task_status
                
                # 构建状态响应
                return EvaluationStatusResponse(
                    id=eval_id,
                    status=status_info.get("status_text", ""),
                    progress=float(status_info.get("progress", 0)),
                    model_name=status_info.get("model_name", ""),
                    dataset_names=status_info.get("dataset_names", ""),
                    results=status_info.get("results", {}),
                    created_at=status_info.get("created_at", datetime.now()),
                    updated_at=status_info.get("updated_at"),
                    task_id=status_info.get("celery_id"),
                    error_message=status_info.get("message") if "error" in status_info else None
                )
        except Exception as task_manager_error:
            logger.warning(f"从TaskManager获取任务状态出错: {str(task_manager_error)}")
            
        # 2. 如果从TaskManager获取失败，尝试从Redis获取状态（Redis不依赖数据库）
        try:
            redis_status = RedisManager.get_task_status(eval_id)
            if redis_status:
                # 如果从Redis获取到状态，且状态是最终状态，直接返回
                final_statuses = [status.value for status in [EvaluationStatus.COMPLETED, EvaluationStatus.FAILED, EvaluationStatus.TERMINATED]]
                if redis_status.get("status") in final_statuses:
                    # 安全处理日期字段
                    created_at = None
                    updated_at = None
                    try:
                        if redis_status.get("created_at"):
                            created_at = datetime.fromisoformat(redis_status.get("created_at"))
                        if redis_status.get("updated_at"):
                            updated_at = datetime.fromisoformat(redis_status.get("updated_at"))
                    except Exception as date_error:
                        logger.warning(f"解析日期出错: {str(date_error)}")
                        created_at = datetime.now()
                    
                    return EvaluationStatusResponse(
                        id=eval_id,
                        status=redis_status.get("status"),
                        progress=float(redis_status.get("progress", 0)),
                        model_name=redis_status.get("model_name", ""),
                        dataset_names=redis_status.get("dataset_names", ""),
                        results=redis_status.get("results", {}),
                        created_at=created_at or datetime.now(),
                        updated_at=updated_at
                    )
        except Exception as redis_error:
            logger.warning(f"从Redis获取任务状态出错: {str(redis_error)}")
        
        # 3. 如果从TaskManager和Redis获取失败，尝试从数据库获取状态
        with db_operation(db) as db_session:
            # 通过存储库获取评估记录
            eval_task = EvaluationRepository.get_evaluation_by_id(db_session, eval_id)
            if not eval_task:
                return None
            
            # 构建基本响应对象
            status_response = EvaluationStatusResponse(
                id=eval_task.id,
                model_name=eval_task.model_name or "",
                dataset_names=eval_task.dataset_names or "",
                status=eval_task.status or EvaluationStatus.UNKNOWN.value,
                progress=0,
                results=eval_task.results or {},
                created_at=eval_task.created_at or datetime.now(),
                updated_at=eval_task.updated_at,
                task_id=eval_task.task_id,
                error_message=eval_task.error_message
            )
            
            
            # 更新Redis缓存
            try:
                status_data = {
                    "id": status_response.id,
                    "status": status_response.status,
                    "progress": status_response.progress,
                    "model_name": status_response.model_name,
                    "dataset_names": status_response.dataset_names,
                    "updated_at": eval_task.updated_at.isoformat() if eval_task.updated_at else None
                }
                RedisManager.update_task_status(eval_id, status_data)
            except Exception as redis_update_error:
                logger.warning(f"更新Redis缓存出错: {str(redis_update_error)}")
                
            return status_response

    
    def get_evaluation_logs(self, eval_id: int, lines: Optional[int] = 50):
        """获取评估任务的日志
        
        Args:
            eval_id: 评估任务ID
            lines: 要获取的日志行数，默认50行
            
        Returns:
            List[str]: 日志行列表
        """
        # 从Redis获取日志
        logs = RedisManager.get_logs(eval_id, max_lines=lines)
        
        if logs:
            return logs
        
        # 如果Redis中没有日志，尝试从运行器获取
        runner = get_runner(eval_id)
        if runner:
            return runner.get_recent_logs(lines)
        
        # 没有找到日志，返回空列表
        return []

    async def list_evaluations(
        self, 
        status: Optional[str] = None, 
        limit: int = 10,
        offset: int = 0, 
        user_id: Optional[int] = None,
        search_query: Optional[str] = None,
        db: Union[Session, Iterator[Session]] = Depends(get_db)
    ):
        """列出评估任务，支持用户筛选和搜索
        
        Args:
            status: 可选的状态过滤条件
            limit: 分页限制，默认10条
            offset: 分页偏移
            user_id: 可选的用户ID过滤
            search_query: 搜索关键词（模型名称或数据集）
            db: 数据库会话
            
        Returns:
            dict: 评估任务列表
        """
        async with async_db_operation(db) as db_session:
            try:
                # 构建查询条件
                query = db_session.query(Evaluation).options(joinedload(Evaluation.user))
                
                # 添加状态过滤
                if status:
                    query = query.filter(Evaluation.status == status)
                    
                # 添加用户过滤
                if user_id:
                    query = query.filter(Evaluation.user_id == user_id)
                    
                # 添加搜索功能
                if search_query:
                    search_pattern = f"%{search_query}%"
                    query = query.filter(
                        or_(
                            Evaluation.model_name.ilike(search_pattern),
                            cast(Evaluation.dataset_names, String).ilike(search_pattern),
                            Evaluation.name.ilike(search_pattern)
                        )
                    )
                
                # 计算总数 - 修改为同步方式
                total_query = select(func.count()).select_from(query.subquery())
                total_result = db_session.execute(total_query)  # 移除 await
                total = total_result.scalar() or 0
                
                # 添加排序和分页
                query = query.order_by(desc(Evaluation.created_at)).offset(offset).limit(limit)
                
                # 执行查询 - 同样需要修改
                result = db_session.execute(query)  # 移除 await
                evaluations = result.unique().all()
                
                # 格式化结果
                items = []
                for eval_task in evaluations:
                    # 从关联的用户对象获取用户信息
                    user_info = {
                        "user_id": eval_task.user_id,
                        "user_name": eval_task.user.display_name if hasattr(eval_task, 'user') and eval_task.user else "未知用户",
                        "user_avatar": eval_task.user.avatar if hasattr(eval_task, 'user') and eval_task.user else "/assets/images/default-avatar.png"
                    }
                    
                    # 构建评测信息
                    eval_info = {
                        "id": eval_task.id,
                        "name": eval_task.name,
                        "model_name": eval_task.model_name,
                        "dataset_names": eval_task.dataset_names,
                        "status": eval_task.status,
                        "created_at": eval_task.created_at,
                        "updated_at": eval_task.updated_at,
                        **user_info  # 合并用户信息
                    }
                    
                    items.append(eval_info)
                    
                # 获取活动任务的最新状态
                for item in items:
                    # 如果任务正在运行，尝试获取最新进度
                    if item.get("status") == EvaluationStatus.RUNNING.value:
                        try:
                            # 从Redis获取最新状态
                            task_status = RedisManager.get_task_status(item.get("id"))
                            if task_status:                           
                                # 如果Redis中的状态与数据库不一致，更新状态
                                redis_status = task_status.get("status")
                                if redis_status and redis_status != item.get("status"):
                                    logger.info(f"更新任务状态 [eval_id={item.get('id')}]: {item.get('status')} -> {redis_status}")
                                    item["status"] = redis_status
                        except Exception as e:
                            logger.warning(f"获取任务最新状态时出错 [eval_id={item.get('id')}]: {str(e)}")
                
                # 构建响应
                return {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }
            except Exception as e:
                logger.exception(f"列出评估任务异常: {str(e)}")
                raise Exception(f"列出评估任务异常: {str(e)}")

   
    async def delete_evaluation(self, eval_id: int, db: Session):
        """删除评估任务
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        # 查询任务是否存在
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not eval_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"评估任务 {eval_id} 不存在"
            )
        
        try:
            # 如果任务正在运行，先尝试终止它
            if eval_task.status in [EvaluationStatus.PENDING.value, EvaluationStatus.RUNNING.value]:
                runner = get_runner(eval_id)
                if runner and runner.is_running:
                    runner.terminate()
            
            # 从数据库中删除任务
            db.delete(eval_task)
            db.commit()
            
            # 清理Redis中的数据
            try:
                RedisManager.delete_task_data(eval_id)
            except Exception as e:
                logger.warning(f"清理Redis数据出错: {str(e)}")
                # 继续执行，不影响主流程
            
            return {"success": True, "message": "任务已成功删除"}
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除任务失败: {str(e)}"
            )
    
    def update_evaluation_name(self, eval_id: int, name: str, db: Session):
        """更新评估任务名称
        
        Args:
            eval_id: 评估任务ID
            name: 新的任务名称
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        # 验证名称是否有效
        if not name or not name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供有效的任务名称"
            )
        
        # 查询任务是否存在
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not eval_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"评估任务 {eval_id} 不存在"
            )
        
        try:
            # 更新任务名称
            eval_task.name = name.strip()
            db.commit()
            db.refresh(eval_task)
            
            # 同时更新Redis中的任务数据
            try:
                status_data = RedisManager.get_task_status(eval_id)
                if status_data:
                    status_data["name"] = eval_task.name
                    RedisManager.set_task_status(eval_id, status_data)
            except Exception as e:
                logger.warning(f"更新Redis数据出错: {str(e)}")
                # 继续执行，不影响主流程
            
            return {
                "success": True, 
                "message": "任务名称已更新",
                "name": eval_task.name
            }
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新任务名称失败: {str(e)}"
            )


    def terminate_evaluation(self, eval_id: int, db: Session) -> Dict[str, Any]:
        """终止评估任务
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 包含操作结果的字典
        """
        try:
            # 调用TaskManager的terminate_task方法
            result = self.task_manager.terminate_task(eval_id)
            if result.get("success"):
                # 正常发送指令后，更新数据库中的任务状态为TERMINATED
                with db_operation(db) as db_session:
                    eval_task = EvaluationRepository.get_evaluation_by_id(db_session, eval_id)
                if eval_task:
                    eval_task.status = EvaluationStatus.TERMINATED.value
                    db_session.commit()
            return result
        except Exception as e:
            logger.error(f"终止评估任务失败 [eval_id={eval_id}]: {str(e)}")
            return {
                "success": False,
                "message": f"终止评估任务失败: {str(e)}"
            }

    def get_evaluation_results(self, eval_id: int, db: Session) -> Dict[str, Any]:
        """获取评测任务的详细结果
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 评测结果详情，如果没有结果则返回None
        """
        with db_operation(db) as db_session:
            # 获取评测记录
            evaluation = db_session.get(Evaluation, eval_id)
            if not evaluation:
                return None
                
            # 检查是否有结果
            if not evaluation.results or not isinstance(evaluation.results, dict):
                return {
                    "id": eval_id,
                    "status": evaluation.status,
                    "model_name": evaluation.model_name,
                    "dataset_names": evaluation.dataset_names,
                    "created_at": evaluation.created_at,
                    "updated_at": evaluation.updated_at,
                    "has_results": False,
                    "message": "评测结果尚未生成或正在处理中"
                }
                
            # 构建结果响应
            result_data = {
                "id": eval_id,
                "status": evaluation.status,
                "model_name": evaluation.model_name,
                "dataset_names": evaluation.dataset_names,
                "created_at": evaluation.created_at,
                "updated_at": evaluation.updated_at,
                "has_results": True,
                "results": evaluation.results
            }
            
            return result_data
            
    def get_evaluation_zip_path(self, eval_id: int, db: Session) -> str:
        """获取评测任务的结果ZIP文件路径
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            str: ZIP文件的完整路径，如果不存在则返回None
        """
        with db_operation(db) as db_session:
            # 获取评测记录
            evaluation = db_session.get(Evaluation, eval_id)
            if not evaluation or not evaluation.results:
                return None
                
            # 尝试从结果中获取归档路径
            archive_path = evaluation.results.get("archive_path")
            if not archive_path:
                # 尝试通过约定的路径查找
                logs_dir = Path(f"logs/eval_{eval_id}")
                if logs_dir.exists():
                    zip_files = list(logs_dir.glob("full_results_*.zip"))
                    if zip_files:
                        # 返回最新的ZIP文件
                        return str(sorted(zip_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                return None
                
            # 验证文件是否存在
            if not os.path.exists(archive_path):
                logger.warning(f"数据库中记录的ZIP文件路径不存在: {archive_path}")
                return None
                
            return archive_path

    def adapt_dify_configuration(self, env_vars: dict, dify2openai_url: str) -> dict:
        """适配Dify平台的特殊配置
        
        Args:
            env_vars: 原始环境变量字典
            dify2openai_url: dify2openai网关地址
            
        Returns:
            适配后的环境变量字典
        """
        # 创建副本避免修改原始数据
        adapted_vars = env_vars.copy()
        
        # 问题：由于dify平台不支持OpenAI标准API，所以我们需要借助dify2openai网关服务进行中转
        # 解决方案：详细查看localhost:3099
        # 1. 原有的env_vars中的API_URL改为settings.dify2openai_url
        # 2. 原有env_vars中的API_KEY保持不变
        # 3. 原有env_vars中的MODEL改为dify|Chat|原有env_vars中的DIFY_URL

        try:
            if adapted_vars.get('api_type') == 'dify':
                # 检查DIFY_TYPE的首字母是否大写，如果没有则将首字母转为大写
                if adapted_vars['DIFY_TYPE'][0].islower():
                    adapted_vars['DIFY_TYPE'] = adapted_vars['DIFY_TYPE'][0].upper() + adapted_vars['DIFY_TYPE'][1:]

                # 构造MODEL参数格式：dify|{类型}|{DIFY_URL}
                adapted_vars['MODEL'] = f"dify|{adapted_vars['DIFY_TYPE']}|{adapted_vars['DIFY_URL']}"
                
                # 更新API相关配置
                adapted_vars.update({
                    'API_URL': dify2openai_url,
                    'API_KEY': adapted_vars['DIFY_API_KEY']
                })
                
                # 移除不再需要的Dify专用参数
                for key in ['DIFY_TYPE', 'DIFY_URL', 'DIFY_API_KEY']:
                    adapted_vars.pop(key, None)
                
        except KeyError as e:
            raise ValueError(f"缺少必要的Dify配置参数: {str(e)}") from e
        
        return adapted_vars
