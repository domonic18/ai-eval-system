from fastapi import Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from apps.server.src.db import get_db, SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from celery.result import AsyncResult
import traceback
from typing import Optional, Union, Iterator, Dict, Any, List, Tuple, Callable, cast
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from apps.server.src.tasks.eval_tasks import run_evaluation
from apps.server.src.utils.redis_manager import RedisManager
from apps.server.src.tasks.opencompass_runner import get_runner
from sqlalchemy import text as sqlalchemy_text
import asyncio
import uuid
from apps.server.src.repositories.evaluation_repository import EvaluationRepository
from apps.server.src.utils.db_utils import db_operation, async_db_operation
from fastapi import HTTPException, status
from fastapi.websockets import WebSocketState
from apps.server.src.tasks.task_manager import TaskManager
from apps.server.src.utils.resource_manager import ResourceManager

# 日志配置
logger = logging.getLogger(__name__)

class EvaluationService:
    """评估服务类，处理评估任务的创建和状态查询"""
    
    def __init__(self):
        """初始化评估服务"""
        self.task_manager = TaskManager()
        self.redis_manager = RedisManager()
    
    async def create_evaluation_task(self, eval_data: EvaluationCreate, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """创建评估任务
        
        使用TaskManager创建并管理评估任务，支持队列和并发控制
        
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
                    
                    # 构建返回对象
                    return EvaluationResponse(
                        id=db_eval.id,
                        model_name=db_eval.model_name,
                        dataset_name=db_eval.dataset_name,
                        status=db_eval.status,
                        created_at=db_eval.created_at,
                        updated_at=db_eval.updated_at,
                        task_id=task_result.get("task_id")
                    )
                else:
                    logger.error(f"评估任务创建失败 [eval_id={db_eval.id}]: {task_result['message']}")
                    raise Exception(task_result["message"])
            except Exception as e:
                logger.exception(f"创建评估任务异常: {str(e)}")
                raise Exception(f"创建评估任务异常: {str(e)}")

    async def legacy_create_evaluation_task(self, eval_data: EvaluationCreate, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """旧版的评估任务创建方法（保留作为备用）
        
        Args:
            eval_data: 评估数据
            db: 数据库会话（可能是 Session 对象或 FastAPI 依赖的生成器）
            
        Returns:
            EvaluationResponse: 评估响应
        """
        from apps.server.src.repositories.evaluation_repository import EvaluationRepository
        from apps.server.src.utils.db_utils import async_db_operation
        from apps.server.src.tasks.eval_tasks import run_evaluation
        import traceback
        
        # 使用异步数据库操作上下文管理器
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

                # 使用存储库创建评估记录（异步）
                db_eval = await EvaluationRepository.create_evaluation_async(
                    db_session,
                    eval_data.model_name,
                    eval_data.dataset_name,
                    model_configuration,
                    dataset_configuration,
                    eval_data.eval_config or {}
                )
                
                # 启动 Celery 任务
                try:
                    # 使用run_evaluation函数创建Celery任务（异步包装）
                    task = await asyncio.to_thread(run_evaluation.delay, db_eval.id)
                    logger.info(f"启动评估任务 {db_eval.id}，Celery 任务 ID: {task.id}")
                    
                    # 异步更新任务ID
                    await EvaluationRepository.update_task_id_async(db_session, db_eval.id, task.id)
                    
                    # 异步获取最新数据
                    db_eval = await EvaluationRepository.get_evaluation_by_id_async(db_session, db_eval.id)
                    
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
                    
                    # 异步更新评估状态为失败
                    await EvaluationRepository.update_error_async(db_session, db_eval.id, f"启动评估任务失败: {str(e)}")
                    
                    # 重新抛出异常
                    raise Exception(f"启动评估任务失败: {str(e)}")
                    
            except SQLAlchemyError as e:
                # 回滚事务
                if db_session:
                    await asyncio.to_thread(db_session.rollback)
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

    def get_evaluation_status(self, eval_id: int, db: Session):
        """获取评估任务状态
        
        优先使用TaskManager获取任务状态，如果失败则回退到数据库查询
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Optional[EvaluationStatusResponse]: 评估任务状态
        """
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
                    dataset_name=status_info.get("dataset_name", ""),
                    results=status_info.get("results", {}),
                    created_at=status_info.get("created_at", datetime.now()),
                    updated_at=status_info.get("updated_at"),
                    task_id=status_info.get("celery_id"),
                    error_message=status_info.get("message") if "error" in status_info else None
                )
        except Exception as task_manager_error:
            logger.warning(f"从TaskManager获取任务状态出错: {str(task_manager_error)}")
            
        # 如果从TaskManager获取失败，尝试从Redis获取状态（Redis不依赖数据库）
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
                        dataset_name=redis_status.get("dataset_name", ""),
                        results=redis_status.get("results", {}),
                        created_at=created_at or datetime.now(),
                        updated_at=updated_at
                    )
        except Exception as redis_error:
            logger.warning(f"从Redis获取任务状态出错: {str(redis_error)}")
        
        # 使用数据库操作上下文管理器
        with db_operation(db) as db_session:
            # 通过存储库获取评估记录
            eval_task = EvaluationRepository.get_evaluation_by_id(db_session, eval_id)
            if not eval_task:
                return None
            
            # 构建基本响应对象
            status_response = EvaluationStatusResponse(
                id=eval_task.id,
                model_name=eval_task.model_name or "",
                dataset_name=eval_task.dataset_name or "",
                status=eval_task.status or EvaluationStatus.UNKNOWN.value,
                progress=0,
                results=eval_task.results or {},
                created_at=eval_task.created_at or datetime.now(),
                updated_at=eval_task.updated_at,
                task_id=eval_task.task_id,
                error_message=eval_task.error_message
            )
            
            # 如果任务正在运行，尝试获取最新进度
            if eval_task.status == EvaluationStatus.RUNNING.value:
                try:
                    # 从任务运行器获取进度
                    runner = get_runner(f"eval_{eval_id}")
                    if runner:
                        status_response.progress = runner.progress
                        
                        # 如果有结果，更新结果
                        results = runner.get_results()
                        if results:
                            status_response.results = results
                    else:
                        # 任务运行器不存在，但任务状态为运行中
                        # 可能是服务重启后丢失了运行器实例
                        # 从数据库获取进度（如果有）
                        if eval_task.results:
                            results_data = eval_task.results
                            if isinstance(results_data, str):
                                try:
                                    import json
                                    results_data = json.loads(results_data)
                                except:
                                    results_data = {}
                            
                            if isinstance(results_data, dict) and "progress" in results_data:
                                status_response.progress = float(results_data.get("progress", 0))
                except Exception as progress_error:
                    logger.warning(f"获取任务进度出错: {str(progress_error)}")
            
            # 更新Redis缓存
            try:
                status_data = {
                    "id": status_response.id,
                    "status": status_response.status,
                    "progress": status_response.progress,
                    "model_name": status_response.model_name,
                    "dataset_name": status_response.dataset_name,
                    "updated_at": eval_task.updated_at.isoformat() if eval_task.updated_at else None
                }
                RedisManager.update_task_status(eval_id, status_data)
            except Exception as redis_update_error:
                logger.warning(f"更新Redis缓存出错: {str(redis_update_error)}")
                
            return status_response

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
        # OpenCompass执行路径，应该在libs/OpenCompass下执行
        opencompass_path = "libs/OpenCompass"
        
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
            "run_command": f"cd {opencompass_path} && python run.py --models {model_name}.py --datasets {dataset_name}.py --debug"
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

    async def handle_websocket_logs(self, websocket: WebSocket, eval_id: int):
        """处理WebSocket日志连接
        
        建立WebSocket连接，发送历史日志，并实时转发新的日志消息
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
        """
        # 接受WebSocket连接
        await websocket.accept()
        
        # 生成唯一的客户端ID
        client_id = str(uuid.uuid4())
        logger.info(f"已建立WebSocket连接 [eval_id={eval_id}, client_id={client_id}]")
        
        # 资源初始化为None
        redis_client = None
        pubsub = None
        heartbeat_task = None
        
        try:
            # 1. 发送当前任务状态
            await self._send_task_status(websocket, eval_id)
            
            # 2. 发送历史日志
            await self._send_historical_logs(websocket, eval_id)
            
            # 3. 订阅Redis日志通道
            redis_client, pubsub = await self._subscribe_to_log_channel(eval_id)
            if not redis_client or not pubsub:
                await websocket.send_json({"error": "无法连接到日志服务"})
                return
                
            # 4. 启动心跳任务
            heartbeat_task = asyncio.create_task(self._websocket_heartbeat(websocket))
            
            # 5. 开始监听并转发日志消息
            await self._listen_for_log_messages(websocket, pubsub)
            
        except WebSocketDisconnect:
            logger.info(f"客户端断开WebSocket连接 [eval_id={eval_id}, client_id={client_id}]")
        except Exception as e:
            logger.error(f"WebSocket处理出错 [eval_id={eval_id}]: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                await websocket.send_json({"error": f"处理日志出错: {str(e)}"})
            except:
                pass
        finally:
            # 取消心跳任务
            if heartbeat_task:
                heartbeat_task.cancel()
                
            # 清理资源
            await self._cleanup_websocket_resources(pubsub, redis_client)
            
            # 尝试关闭WebSocket
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
                
            logger.info(f"WebSocket连接已关闭 [eval_id={eval_id}, client_id={client_id}]")

    async def _send_task_status(self, websocket: WebSocket, eval_id: int):
        """发送任务当前状态信息
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
        """
        try:
            status_data = RedisManager.get_task_status(eval_id)
            if status_data:
                await websocket.send_json({
                    "type": "status",
                    "data": status_data
                })
                logger.debug(f"已发送任务状态 [eval_id={eval_id}]")
        except Exception as e:
            logger.warning(f"发送任务状态失败 [eval_id={eval_id}]: {str(e)}")

    async def _send_historical_logs(self, websocket: WebSocket, eval_id: int):
        """发送历史日志到WebSocket
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
        """
        try:
            # 从Redis获取历史日志
            logs = RedisManager.get_logs(eval_id, max_lines=200)
            
            if logs and len(logs) > 0:
                logger.debug(f"从Redis获取到{len(logs)}条历史日志 [eval_id={eval_id}]")
                await websocket.send_json({
                    "type": "info", 
                    "data": f"已加载{len(logs)}条历史日志"
                })
                
                # 批量发送日志以提高性能
                for log_line in logs:
                    await websocket.send_text(log_line)
            else:
                logger.debug(f"Redis中无历史日志 [eval_id={eval_id}]")
                await websocket.send_json({
                    "type": "info", 
                    "data": "暂无历史日志"
                })
        except Exception as e:
            logger.warning(f"发送历史日志失败 [eval_id={eval_id}]: {str(e)}")
            await websocket.send_json({
                "type": "warning", 
                "data": f"获取历史日志失败: {str(e)}"
            })

    async def _subscribe_to_log_channel(self, eval_id: int):
        """订阅Redis日志通道
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            Tuple[redis.Redis, redis.client.PubSub]: Redis客户端和PubSub对象
        """
        try:
            # 获取Redis连接
            redis_client = RedisManager.get_instance()
            if not redis_client:
                logger.error(f"无法获取Redis客户端 [eval_id={eval_id}]")
                return None, None
                
            # 创建PubSub对象并订阅日志通道
            pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            log_channel = RedisManager.get_log_channel(eval_id)
            pubsub.subscribe(log_channel)
            
            logger.debug(f"已订阅Redis日志通道 [eval_id={eval_id}, channel={log_channel}]")
            return redis_client, pubsub
        except Exception as e:
            logger.error(f"订阅日志通道失败 [eval_id={eval_id}]: {str(e)}")
            return None, None

    async def _websocket_heartbeat(self, websocket: WebSocket):
        """定期发送心跳消息，保持WebSocket连接活跃
        
        Args:
            websocket: WebSocket连接
        """
        try:
            while True:
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                    
                await websocket.send_json({"type": "heartbeat"})
                await asyncio.sleep(30)  # 每30秒发送一次心跳
        except Exception as e:
            logger.debug(f"心跳发送失败: {str(e)}")

    async def _listen_for_log_messages(self, websocket: WebSocket, pubsub):
        """监听Redis日志消息并转发到WebSocket
        
        Args:
            websocket: WebSocket连接
            pubsub: Redis PubSub对象
        """
        logger.debug("开始监听Redis日志消息")
        
        while True:
            # 1. 检查WebSocket连接状态
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.debug("WebSocket连接已断开，停止监听")
                break
                
            try:
                # 2. 非阻塞方式获取消息
                message = pubsub.get_message(timeout=0.1)
                
                # 3. 处理消息
                if message and message["type"] == "message":
                    # 解析消息内容
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                        
                    # 发送到WebSocket
                    await websocket.send_text(data)
                    
                # 4. 短暂休眠，避免CPU占用过高
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.warning(f"处理Redis消息失败: {str(e)}")
                if "connection closed" in str(e).lower() or "close message has been sent" in str(e).lower():
                    break

    async def _cleanup_websocket_resources(self, pubsub=None, redis_client=None):
        """清理WebSocket相关资源
        
        Args:
            pubsub: Redis PubSub对象
            redis_client: Redis客户端
        """
        # 关闭PubSub
        if pubsub:
            try:
                pubsub.unsubscribe()
                pubsub.close()
                logger.debug("已关闭Redis PubSub连接")
            except Exception as e:
                logger.warning(f"关闭PubSub连接失败: {str(e)}")

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
        runner = get_runner(f"eval_{eval_id}")
        if runner:
            return runner.get_recent_logs(lines)
        
        # 没有找到日志，返回空列表
        return []

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
                runner = get_runner(f"eval_{eval_id}")
                if runner and runner.is_running:
                    runner.terminate()
            
            # 从数据库中删除任务
            db.delete(eval_task)
            db.commit()
            
            # 清理Redis中的数据
            try:
                await RedisManager.delete_task_data(eval_id)
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

# 创建服务实例
evaluation_service = EvaluationService()

# 为了简化路由层调用，导出服务实例方法
async def create_evaluation_task(eval_data, db: Union[Session, Iterator[Session]] = Depends(get_db)):
    return await evaluation_service.create_evaluation_task(eval_data, db)

def get_evaluation_status(eval_id: int, db: Session):
    return evaluation_service.get_evaluation_status(eval_id, db)

def list_evaluations(db: Session):
    return evaluation_service.list_evaluations(db)

def get_evaluation_logs(eval_id: int, lines: Optional[int] = 50):
    return evaluation_service.get_evaluation_logs(eval_id, lines)

def terminate_evaluation(eval_id: int, db: Session):
    return evaluation_service.terminate_evaluation(eval_id, db)

async def delete_evaluation(eval_id: int, db: Session):
    """删除评估任务
    
    Args:
        eval_id: 评估任务ID
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    return await evaluation_service.delete_evaluation(eval_id, db)

def update_evaluation_name(eval_id: int, name: str, db: Session):
    return evaluation_service.update_evaluation_name(eval_id, name, db)

# 为了WebSocket处理，导出服务实例
async def handle_websocket_logs(websocket: WebSocket, eval_id: int):
    """WebSocket日志处理的入口函数
    
    Args:
        websocket: WebSocket连接
        eval_id: 评估任务ID
    """
    await evaluation_service.handle_websocket_logs(websocket, eval_id) 