import logging
import traceback
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from fastapi import HTTPException, status
from typing import Optional, Union, Iterator, Dict, Any, List, Tuple, Callable, cast
from models.eval import Evaluation, EvaluationStatus
from schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from api.deps import get_db
from utils.utils_db import async_db_operation
from tasks.task_manager import TaskManager
from repositories.evaluation_repository import EvaluationRepository
from utils.redis_manager import RedisManager
from tasks.runners.runner import get_runner

# from utils.logger import get_logger
# from tasks.eval_tasks import run_evaluation_task


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
        # 创建评估记录
        db_eval = await EvaluationRepository.create_evaluation_async(
            db,
            eval_data.model_name,
            eval_data.dataset_name,
            eval_data.model_configuration,
            eval_data.dataset_configuration,
            eval_data.eval_config or {}
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
            dataset_name=db_eval.dataset_name,
            status=db_eval.status,
            created_at=db_eval.created_at,
            updated_at=db_eval.updated_at,
            task_id=task_result["task_id"]
        )

    def get_evaluation_status(self, eval_id: int, db: Session):
        """获取评估任务状态
        
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
                    runner = get_runner(eval_id)
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

    async def handle_websocket_logs(self, websocket: WebSocket, eval_id: int):
        """处理WebSocket日志连接
        
        将WebSocket日志处理逻辑从路由层移到服务层，提高代码可维护性
        
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
            redis_client, pubsub = await self._subscribe_to_log_channel(websocket, eval_id)
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
    async def _subscribe_to_log_channel(self, websocket: WebSocket, eval_id: int):
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
    async def _get_evaluation_for_websocket(self, eval_id: int) -> Optional[Evaluation]:
        """获取评估任务信息用于WebSocket处理
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            Optional[Evaluation]: 评估任务对象，如果不存在则返回None
        """
        pass
    
    async def _update_task_status_for_websocket(self, websocket: WebSocket, eval_task: Evaluation):
        """为WebSocket连接更新任务状态到Redis
        
        Args:
            websocket: WebSocket连接
            eval_task: 评估任务对象
        """
        pass
    

    async def _cleanup_websocket_resources(self, websocket: WebSocket, pubsub=None, redis=None):
        """清理WebSocket相关资源
        
        Args:
            websocket: WebSocket连接
            pubsub: Redis PubSub对象
            redis: Redis连接对象
        """
        pass

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

    async def list_evaluations(self, status: Optional[str] = None, limit: int = 100, offset: int = 0, db: Union[Session, Iterator[Session]] = Depends(get_db)):
        """获取所有评估任务列表
        
        Args:
            db: 数据库会话
            
        Returns:
            dict: 评估任务列表
        """
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
                
                # 获取活动任务的最新状态
                items = evaluations.get("items", [])
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
                    "total": evaluations.get("total", 0),
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
            return result
        except Exception as e:
            logger.error(f"终止评估任务失败 [eval_id={eval_id}]: {str(e)}")
            return {
                "success": False,
                "message": f"终止评估任务失败: {str(e)}"
            }

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
