#!/usr/bin/env python3
# 评估数据存储库

import logging
import json
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from models.eval import Evaluation, EvaluationStatus
import asyncio

logger = logging.getLogger(__name__)

class EvaluationRepository:
    """评估数据存储库类
    
    处理所有与评估相关的数据库操作，提高代码可维护性和可重用性
    """
    
    @staticmethod
    def create_evaluation(
        db: Session, 
        model_name: str, 
        dataset_names: List[str], 
        model_configuration: Dict[str, Any], 
        dataset_configuration: Dict[str, Any], 
        eval_config: Dict[str, Any] = None
    ) -> Evaluation:
        """创建新的评估记录
        
        Args:
            db: 数据库会话
            model_name: 模型名称
            dataset_names: 数据集名称列表
            model_configuration: 模型配置
            dataset_configuration: 数据集配置
            eval_config: 评估配置
            
        Returns:
            Evaluation: 创建的评估记录
        """
        db_eval = Evaluation(
            model_name=model_name,
            dataset_names=json.dumps(dataset_names),
            model_configuration=model_configuration,
            dataset_configuration=dataset_configuration,
            eval_config=eval_config or {},
            status=EvaluationStatus.PENDING.value,
            log_dir="logs/default"  # 设置一个默认值，避免空字符串
        )
            
        # 添加并提交
        db.add(db_eval)
        db.commit()
        db.refresh(db_eval)
        
        return db_eval
    
    @staticmethod
    def get_evaluation_by_id(db: Session, eval_id: int) -> Optional[Evaluation]:
        """根据ID获取评估记录
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            
        Returns:
            Optional[Evaluation]: 找到的评估记录或None
        """
        return db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    
    @staticmethod
    def update_log_dir(db: Session, eval_id: int, log_dir: str) -> bool:
        """更新评估记录的日志目录
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            log_dir: 日志目录
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_stmt = text("UPDATE evaluations SET log_dir = :log_dir WHERE id = :id")
            db.execute(update_stmt, {"log_dir": log_dir, "id": eval_id})
            db.commit()
            return True
        except Exception as e:
            logger.error(f"更新日志目录失败: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def update_task_id(db: Session, eval_id: int, task_id: str) -> bool:
        """更新评估记录的Celery任务ID
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            task_id: Celery任务ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_stmt = text("UPDATE evaluations SET task_id = :task_id WHERE id = :id")
            db.execute(update_stmt, {"task_id": task_id, "id": eval_id})
            db.commit()
            return True
        except Exception as e:
            logger.error(f"更新任务ID失败: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def update_status(db: Session, eval_id: int, status: EvaluationStatus, results: Dict[str, Any] = None) -> bool:
        """更新评估记录的状态和结果
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            status: 评估状态
            results: 评估结果
            
        Returns:
            bool: 更新是否成功
        """
        try:
            eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if eval_task:
                eval_task.status = status.value
                if results:
                    eval_task.results = results
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def update_error(db: Session, eval_id: int, error_message: str) -> bool:
        """更新评估记录的错误信息
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            error_message: 错误信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if eval_task:
                eval_task.status = EvaluationStatus.FAILED.value
                eval_task.error_message = error_message
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"更新错误信息失败: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    async def create_evaluation_async(
        db: Session, 
        model_name: str, 
        dataset_names: List[str],
        model_configuration: Dict[str, Any], 
        dataset_configuration: Dict[str, Any], 
        eval_config: Dict[str, Any] = None,
        env_vars: Dict[str, Any] = {}
    ) -> Evaluation:
        """异步创建新的评估记录
        
        Args:
            db: 数据库会话
            model_name: 模型名称
            dataset_names: 数据集名称列表
            model_configuration: 模型配置
            dataset_configuration: 数据集配置
            eval_config: 评估配置
            env_vars: 环境变量
        Returns:
            Evaluation: 创建的评估记录
        """
        try:
            db_eval = Evaluation(
                model_name=model_name,
                dataset_names=json.dumps(dataset_names),
                model_configuration=model_configuration,
                dataset_configuration=dataset_configuration,
                eval_config=eval_config or {},
                status=EvaluationStatus.PENDING.value,
                log_dir="logs/default",
                progress=0.0,
                env_vars=env_vars
            )
        
            # 添加并提交(异步执行)
            db.add(db_eval)
            await asyncio.to_thread(db.commit)
            await asyncio.to_thread(db.refresh, db_eval)
        except Exception as e:
            logger.error(f"异步创建评估记录失败: {str(e)}")
            raise e
        
        return db_eval
    
    @staticmethod
    async def update_task_id_async(db: Session, eval_id: int, task_id: str) -> bool:
        """异步更新评估记录的Celery任务ID
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            task_id: Celery任务ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_stmt = text("UPDATE evaluations SET task_id = :task_id, status = :status, updated_at = :updated_at WHERE id = :id")
            params = {
                "task_id": task_id, 
                "status": EvaluationStatus.RUNNING.value,
                "updated_at": datetime.now(),
                "id": eval_id
            }
            await asyncio.to_thread(lambda: db.execute(update_stmt, params))
            await asyncio.to_thread(db.commit)
            return True
        except Exception as e:
            logger.error(f"异步更新任务ID失败: {str(e)}")
            await asyncio.to_thread(db.rollback)
            return False
            
    @staticmethod
    async def update_error_async(db: Session, eval_id: int, error_message: str) -> bool:
        """异步更新评估记录的错误信息
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            error_message: 错误信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            update_stmt = text("""
                UPDATE evaluations 
                SET status = :status, 
                    error_message = :error_message, 
                    updated_at = :updated_at 
                WHERE id = :id
            """)
            params = {
                "status": EvaluationStatus.FAILED.value,
                "error_message": error_message,
                "updated_at": datetime.now(),
                "id": eval_id
            }
            await asyncio.to_thread(lambda: db.execute(update_stmt, params))
            await asyncio.to_thread(db.commit)
            return True
        except Exception as e:
            logger.error(f"异步更新错误信息失败: {str(e)}")
            await asyncio.to_thread(db.rollback)
            return False
            
    @staticmethod
    async def get_evaluation_by_id_async(db: Session, eval_id: int) -> Optional[Evaluation]:
        """异步获取评估记录
        
        Args:
            db: 数据库会话
            eval_id: 评估ID
            
        Returns:
            Optional[Evaluation]: 找到的评估记录或None
        """
        try:
            result = await asyncio.to_thread(
                lambda: db.query(Evaluation).filter(Evaluation.id == eval_id).first()
            )
            return result
        except Exception as e:
            logger.error(f"异步获取评估记录失败: {str(e)}")
            return None
            
    @staticmethod
    async def list_evaluations_async(db: Session, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """异步获取评估任务列表
        
        Args:
            db: 数据库会话
            status: 可选的状态过滤
            limit: 结果数量限制
            offset: 分页偏移量
            
        Returns:
            Dict[str, Any]: 包含评估列表和总数的字典
        """
        try:
            # 构建查询
            query = db.query(Evaluation)
            
            # 应用状态过滤
            if status:
                query = query.filter(Evaluation.status == status)
                
            # 获取总数
            total_count = await asyncio.to_thread(lambda: query.count())
            
            # 应用分页并执行查询
            query = query.order_by(Evaluation.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            # 执行查询并获取结果
            evaluations = await asyncio.to_thread(lambda: query.all())
            
            # 格式化结果
            items = []
            for eval_task in evaluations:
                items.append({
                    "id": eval_task.id,
                    "model_name": eval_task.model_name,
                    "dataset_names": eval_task.dataset_names,
                    "status": eval_task.status,
                    "log_dir": eval_task.log_dir,
                    "task_id": eval_task.task_id,
                    "results": eval_task.results,
                    "created_at": eval_task.created_at.isoformat() if eval_task.created_at else None,
                    "updated_at": eval_task.updated_at.isoformat() if eval_task.updated_at else None,
                    "error_message": eval_task.error_message,
                    "name": eval_task.name
                })
                
            return {
                "items": items,
                "total": total_count,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"异步获取评估列表失败: {str(e)}")
            return {"items": [], "total": 0, "limit": limit, "offset": offset} 