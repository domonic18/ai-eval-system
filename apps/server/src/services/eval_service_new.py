"""评估服务

处理评估任务的创建、查询和终止。
使用TaskManager进行任务管理，确保异步执行和并发控制。
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Optional, Union, Iterator, Dict, Any, List

from fastapi import Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from apps.server.src.db import get_db
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from apps.server.src.tasks.task_manager import TaskManager
from apps.server.src.utils.db_utils import async_db_operation
from apps.server.src.repositories.evaluation_repository import EvaluationRepository
from apps.server.src.utils.redis_manager import RedisManager

# 配置日志
logger = logging.getLogger(__name__)

class EvaluationService:
    """评估服务，处理评估任务的创建和管理"""
    
    def __init__(self):
        """初始化评估服务"""
        self.task_manager = TaskManager()
        self.redis_manager = RedisManager()
    
    async def create_evaluation_task(self, eval_data: EvaluationCreate, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """创建评估任务
        
        Args:
            eval_data: 评估数据
            db: 数据库会话
            
        Returns:
            dict: 创建结果
        """
        async with async_db_operation(db) as db_session:
            try:
                # 验证输入数据
                if not eval_data.model_name:
                    raise ValueError("模型名称不能为空")
                if not eval_data.dataset_name:
                    raise ValueError("数据集名称不能为空")
                
                # 解析模型配置
                model_configuration = {}
                if eval_data.model_configuration:
                    try:
                        if isinstance(eval_data.model_configuration, str):
                            model_configuration = json.loads(eval_data.model_configuration)
                        else:
                            model_configuration = eval_data.model_configuration
                    except json.JSONDecodeError:
                        model_configuration = {"config_error": "无效的 JSON 格式"}
                
                # 解析数据集配置
                dataset_configuration = {}
                if eval_data.dataset_configuration:
                    try:
                        if isinstance(eval_data.dataset_configuration, str):
                            dataset_configuration = json.loads(eval_data.dataset_configuration)
                        else:
                            dataset_configuration = eval_data.dataset_configuration
                    except json.JSONDecodeError:
                        dataset_configuration = {"config_error": "无效的 JSON 格式"}
                
                # 创建评估记录
                db_eval = await EvaluationRepository.create_evaluation_async(
                    db_session,
                    eval_data.model_name,
                    eval_data.dataset_name,
                    model_configuration,
                    dataset_configuration,
                    eval_data.eval_config or {}
                )
                
                # 使用任务管理器创建任务
                task_result = self.task_manager.create_task(db_eval.id, db_session)
                
                if task_result["success"]:
                    logger.info(f"评估任务创建成功 [eval_id={db_eval.id}, task_id={task_result['task_id']}]")
                    
                    # 返回结果
                    return {
                        "success": True,
                        "task_id": task_result["task_id"],
                        "eval_id": db_eval.id,
                        "status": EvaluationStatus.PENDING,
                        "message": "任务已提交"
                    }
                else:
                    logger.error(f"评估任务创建失败 [eval_id={db_eval.id}]: {task_result['message']}")
                    
                    # 返回错误信息
                    return {
                        "success": False,
                        "eval_id": db_eval.id,
                        "message": task_result["message"]
                    }
            except Exception as e:
                logger.exception(f"创建评估任务异常: {str(e)}")
                
                # 返回错误信息
                return {
                    "success": False,
                    "message": f"创建评估任务异常: {str(e)}"
                }
    
    def get_evaluation_status(self, eval_id: int):
        """获取评估任务状态
        
        Args:
            eval_id: 评估ID
            
        Returns:
            dict: 任务状态信息
        """
        try:
            # 使用任务管理器获取任务状态
            task_status = self.task_manager.get_task_status(eval_id)
            
            if not task_status.get("success", False):
                # 如果任务不存在于任务管理器中，则从数据库查询
                with get_db() as db:
                    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                    
                    if not evaluation:
                        return {
                            "success": False,
                            "message": "找不到评估任务"
                        }
                    
                    # 构建状态响应
                    return {
                        "success": True,
                        "eval_id": evaluation.id,
                        "task_id": evaluation.task_id,
                        "status": evaluation.status,
                        "progress": evaluation.progress,
                        "created_at": evaluation.created_at,
                        "updated_at": evaluation.updated_at,
                        "message": evaluation.message
                    }
            
            # 返回任务管理器中的状态信息
            return task_status
        except Exception as e:
            logger.exception(f"获取评估任务状态异常 [eval_id={eval_id}]: {str(e)}")
            
            # 返回错误信息
            return {
                "success": False,
                "message": f"获取评估任务状态异常: {str(e)}"
            }
    
    def terminate_evaluation(self, eval_id: int):
        """终止评估任务
        
        Args:
            eval_id: 评估ID
            
        Returns:
            dict: 终止结果
        """
        try:
            # 使用任务管理器终止任务
            result = self.task_manager.terminate_task(eval_id)
            
            if not result.get("success", False):
                # 如果任务不存在于任务管理器中，则从数据库更新状态
                with get_db() as db:
                    evaluation = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                    
                    if not evaluation:
                        return {
                            "success": False,
                            "message": "找不到评估任务"
                        }
                    
                    # 如果任务不是正在运行状态，则无需终止
                    if evaluation.status != EvaluationStatus.RUNNING:
                        return {
                            "success": True,
                            "message": f"任务当前状态为 {evaluation.status}，无需终止"
                        }
                    
                    # 更新任务状态为已终止
                    evaluation.status = EvaluationStatus.TERMINATED
                    evaluation.updated_at = datetime.now()
                    evaluation.message = "任务已手动终止"
                    db.commit()
                    
                    # 返回结果
                    return {
                        "success": True,
                        "message": "任务已终止"
                    }
            
            # 返回任务管理器的终止结果
            return result
        except Exception as e:
            logger.exception(f"终止评估任务异常 [eval_id={eval_id}]: {str(e)}")
            
            # 返回错误信息
            return {
                "success": False,
                "message": f"终止评估任务异常: {str(e)}"
            }
    
    async def list_evaluations(self, status: Optional[str] = None, limit: int = 100, offset: int = 0, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """列出评估任务
        
        Args:
            status: 可选的状态过滤条件
            limit: 分页限制
            offset: 分页偏移
            db: 数据库会话
            
        Returns:
            dict: 评估任务列表
        """
        async with async_db_operation(db) as db_session:
            try:
                # 获取评估任务列表
                evaluations = await EvaluationRepository.list_evaluations_async(
                    db_session,
                    status,
                    limit,
                    offset
                )
                
                # 构建响应
                return {
                    "success": True,
                    "total": evaluations.get("total", 0),
                    "items": evaluations.get("items", []),
                    "limit": limit,
                    "offset": offset
                }
            except Exception as e:
                logger.exception(f"列出评估任务异常: {str(e)}")
                
                # 返回错误信息
                return {
                    "success": False,
                    "message": f"列出评估任务异常: {str(e)}"
                }
    
    async def register_websocket(self, eval_id: int, websocket: WebSocket):
        """注册WebSocket连接以接收任务日志
        
        Args:
            eval_id: 评估ID
            websocket: WebSocket连接
        """
        try:
            # 接受WebSocket连接
            await websocket.accept()
            
            # 订阅Redis日志通道
            pubsub = self.redis_manager.client.pubsub()
            channel = f"log:eval:{eval_id}"
            pubsub.subscribe(channel)
            
            # 发送历史日志
            historical_logs = self.redis_manager.get_logs(eval_id)
            if historical_logs:
                await websocket.send_text(json.dumps({
                    "type": "historical_logs",
                    "data": historical_logs
                }))
            
            # 发送实时日志
            try:
                for message in pubsub.listen():
                    if message["type"] == "message":
                        # 检查WebSocket连接是否仍然活跃
                        if websocket.client_state == websocket.application_state == WebSocket.CONNECTED:
                            try:
                                await websocket.send_text(message["data"].decode("utf-8"))
                            except Exception as ws_error:
                                logger.warning(f"发送WebSocket消息异常: {str(ws_error)}")
                                break
                        else:
                            logger.warning(f"WebSocket连接已关闭，停止发送日志 [eval_id={eval_id}]")
                            break
            except WebSocketDisconnect:
                logger.info(f"WebSocket连接已断开 [eval_id={eval_id}]")
            finally:
                # 取消订阅并关闭
                pubsub.unsubscribe(channel)
                pubsub.close()
        except Exception as e:
            logger.exception(f"WebSocket处理异常 [eval_id={eval_id}]: {str(e)}")
            try:
                await websocket.close()
            except:
                pass

# 创建评估服务实例
evaluation_service = EvaluationService() 