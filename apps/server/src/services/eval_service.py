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
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Optional[EvaluationStatusResponse]: 评估任务状态
        """
        from apps.server.src.repositories.evaluation_repository import EvaluationRepository
        from apps.server.src.utils.db_utils import db_operation
        
        try:
            # 首先尝试从Redis获取任务状态（Redis不依赖数据库）
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
                    logger.warning(f"更新Redis任务状态缓存出错: {str(redis_update_error)}")
                
                return status_response
        
        except Exception as e:
            logger.error(f"获取评估任务状态出错: {str(e)}")
            logger.error(traceback.format_exc())
            raise

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
        
        将WebSocket日志处理逻辑从路由层移到服务层，提高代码可维护性
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
        """
        # 提前声明资源变量，以便在finally中安全释放
        db_session = None
        pubsub = None
        redis = None
        client_id = None
        
        try:
            # 验证任务存在性
            eval_task = await self._get_evaluation_for_websocket(eval_id)
            if not eval_task:
                await websocket.send_json({"error": f"评估任务 {eval_id} 不存在"})
                await websocket.close()
                return
            
            # 发送历史日志
            await self._send_historical_logs(websocket, eval_id)
            
            # 更新任务状态到Redis
            await self._update_task_status_for_websocket(websocket, eval_task)
            
            # 订阅Redis日志通道
            pubsub, redis, client_id = await self._subscribe_to_log_channel(websocket, eval_id)
            
            # 如果一切正常，持续监听Redis消息
            if pubsub and redis:
                await self._listen_for_log_messages(websocket, pubsub)
                
        except WebSocketDisconnect:
            logger.info(f"客户端断开WebSocket连接: {eval_id}")
        except Exception as e:
            logger.error(f"WebSocket错误: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                await websocket.send_json({"error": f"发生错误: {str(e)}"})
            except:
                pass
        finally:
            # 清理资源
            if client_id:
                RedisManager.unregister_websocket(eval_id, client_id)
            await self._cleanup_websocket_resources(websocket, pubsub, redis)

    async def _get_evaluation_for_websocket(self, eval_id: int) -> Optional[Evaluation]:
        """获取评估任务信息用于WebSocket处理
        
        Args:
            eval_id: 评估任务ID
            
        Returns:
            Optional[Evaluation]: 评估任务对象，如果不存在则返回None
        """
        try:
            # 安全获取数据库会话
            from apps.server.src.db import SessionLocal
            db_session = SessionLocal()
            
            try:
                return db_session.query(Evaluation).filter(Evaluation.id == eval_id).first()
            finally:
                # 确保数据库会话关闭
                if db_session:
                    db_session.close()
        except Exception as db_error:
            logger.error(f"获取评估任务数据库错误: {str(db_error)}")
            return None
            
    async def _send_historical_logs(self, websocket: WebSocket, eval_id: int):
        """发送历史日志到WebSocket
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
        """
        # 先获取Redis中现有的日志
        existing_logs = RedisManager.get_logs(eval_id, max_lines=200)
        if existing_logs:
            await websocket.send_json({"info": f"已加载{len(existing_logs)}条历史日志"})
            # 一次性发送所有日志，而不是逐行发送，减少WebSocket通信次数
            for log_line in existing_logs:
                await websocket.send_text(log_line)
        else:
            # 如果Redis中没有日志，尝试从文件加载
            try:
                BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
                logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
                os.makedirs(logs_dir, exist_ok=True)
                
                log_pattern = f"eval_{eval_id}_*.log"
                log_files = list(Path(logs_dir).glob(log_pattern))
                
                if log_files:
                    log_file = str(sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                    await websocket.send_json({"info": f"从文件加载日志: {os.path.basename(log_file)}"})
                    
                    # 读取文件
                    with open(log_file, 'r') as f:
                        lines = f.read().splitlines()
                        # 限制发送的行数
                        recent_lines = lines[-200:] if len(lines) > 200 else lines
                        
                        # 使用集合去重日志行
                        processed_lines = set()
                        unique_lines = []
                        
                        for line in recent_lines:
                            line = line.strip()
                            if line and line not in processed_lines:
                                processed_lines.add(line)
                                unique_lines.append(line)
                        
                        # 首先清空旧日志
                        RedisManager.clear_logs(eval_id)
                        
                        # 添加到Redis并发送
                        for line in unique_lines:
                            RedisManager.append_log(eval_id, line)
                            await websocket.send_text(line)
                        
                        await websocket.send_json({"info": f"已从文件加载并去重后的{len(unique_lines)}条日志"})
                else:
                    await websocket.send_json({"info": f"任务 {eval_id} 暂无日志"})
            except Exception as file_error:
                logger.warning(f"读取日志文件时出错: {str(file_error)}")
                await websocket.send_json({"warning": f"读取日志文件时出错: {str(file_error)}"})
    
    async def _update_task_status_for_websocket(self, websocket: WebSocket, eval_task: Evaluation):
        """为WebSocket连接更新任务状态到Redis
        
        Args:
            websocket: WebSocket连接
            eval_task: 评估任务对象
        """
        try:
            progress = 0
            if eval_task.results:
                results_data = eval_task.results
                if isinstance(results_data, str):
                    import json
                    results_data = json.loads(results_data)
                if isinstance(results_data, dict):
                    progress = float(results_data.get("progress", 0))
                    
            status_data = {
                "id": eval_task.id,
                "status": eval_task.status.upper() if eval_task.status else "UNKNOWN",
                "progress": progress,
                "model_name": eval_task.model_name or "未知模型",
                "dataset_name": eval_task.dataset_name or "未知数据集",
                "updated_at": eval_task.updated_at.isoformat() if eval_task.updated_at else None
            }
            RedisManager.update_task_status(eval_task.id, status_data)
        except Exception as status_error:
            logger.warning(f"更新任务状态时出错: {str(status_error)}")
            await websocket.send_json({"warning": f"更新任务状态时出错: {str(status_error)}"})
    
    async def _subscribe_to_log_channel(self, websocket: WebSocket, eval_id: int):
        """订阅Redis日志通道
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
            
        Returns:
            Tuple[Optional[aioredis.client.PubSub], Optional[aioredis.client.Redis]]: Redis PubSub和连接对象
        """
        try:
            # 生成唯一的客户端ID
            client_id = str(uuid.uuid4())
            
            # 使用增强的订阅方法
            pubsub = await RedisManager.subscribe_to_logs(eval_id, client_id)
            if not pubsub:
                await websocket.send_json({"error": "无法订阅日志通道"})
                return None, None, None
            
            # 获取Redis连接用于后续操作
            redis = await RedisManager.get_async_instance()
            
            # 发送初始连接成功消息
            await websocket.send_json({
                "info": f"已连接到任务 {eval_id} 的日志订阅",
                "client_id": client_id
            })
            
            return pubsub, redis, client_id
        except Exception as redis_error:
            logger.error(f"Redis订阅错误: {str(redis_error)}")
            await websocket.send_json({"error": f"日志订阅出错: {str(redis_error)}"})
            return None, None, None
            
    async def _listen_for_log_messages(self, websocket: WebSocket, pubsub):
        """监听Redis日志消息并转发到WebSocket
        
        Args:
            websocket: WebSocket连接
            pubsub: Redis PubSub对象
        """
        # 设置超时，避免无限等待
        timeout = 0.1  # 100毫秒超时
        reconnect_count = 0
        max_reconnect_attempts = 3
        
        try:
            while True:
                # 检查WebSocket连接状态
                if not websocket.client_state.CONNECTED:
                    logger.debug("WebSocket连接已断开，停止日志监听")
                    break
                
                try:
                    # 非阻塞方式获取消息，避免长时间阻塞事件循环
                    message = await asyncio.wait_for(pubsub.get_message(), timeout=timeout)
                    
                    if message and message["type"] == "message":
                        # 解析消息内容
                        try:
                            data = message["data"]
                            if isinstance(data, bytes):
                                data = data.decode('utf-8')
                                
                            # 尝试解析JSON格式
                            payload = json.loads(data)
                            log_line = payload.get("log", "")
                            
                            if log_line:
                                await websocket.send_text(log_line)
                        except json.JSONDecodeError:
                            # 兼容旧格式：直接发送文本
                            await websocket.send_text(data)
                        except Exception as parse_error:
                            logger.warning(f"解析日志消息失败: {str(parse_error)}")
                    
                    # 重置重连计数器
                    if reconnect_count > 0:
                        reconnect_count = 0
                        
                    # 短暂休眠，让出控制权给其他协程
                    await asyncio.sleep(0.01)
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环
                    await asyncio.sleep(0.01)
                except Exception as message_error:
                    # 处理消息获取出错
                    logger.warning(f"获取Redis消息出错: {str(message_error)}")
                    reconnect_count += 1
                    
                    if reconnect_count >= max_reconnect_attempts:
                        logger.error(f"Redis连接重试超过{max_reconnect_attempts}次，停止监听")
                        await websocket.send_json({"error": f"日志监听失败: {str(message_error)}"})
                        break
                        
                    # 指数退避重试
                    retry_delay = 0.1 * (2 ** reconnect_count)
                    await asyncio.sleep(retry_delay)
        except Exception as e:
            # 其他错误记录日志
            logger.warning(f"日志监听循环出错: {str(e)}")
            try:
                await websocket.send_json({"error": f"日志监听出错: {str(e)}"})
            except Exception:
                pass  # 忽略发送错误消息可能的异常

    async def _cleanup_websocket_resources(self, websocket: WebSocket, pubsub=None, redis=None):
        """清理WebSocket相关资源
        
        Args:
            websocket: WebSocket连接
            pubsub: Redis PubSub对象
            redis: Redis连接对象
        """
        try:
            if pubsub:
                await pubsub.unsubscribe()
                await pubsub.close()
            
            if redis:
                await redis.close()
                
            await websocket.close()
        except Exception as cleanup_error:
            logger.error(f"清理WebSocket资源时出错: {str(cleanup_error)}")

    def list_evaluations(self, db: Session):
        """获取所有评估任务列表
        
        Args:
            db: 数据库会话
            
        Returns:
            List[Dict[str, Any]]: 评估任务列表
        """
        try:
            # 直接使用db对象查询所有评估任务
            evaluations = db.query(Evaluation).all()
            result = []
            
            for eval_task in evaluations:
                # 安全处理progress字段
                progress = 0.0
                try:
                    if eval_task.results:
                        # 如果results是字符串，尝试解析为字典
                        results_data = eval_task.results
                        if isinstance(results_data, str):
                            import json
                            results_data = json.loads(results_data)
                        
                        if isinstance(results_data, dict) and "progress" in results_data:
                            progress = float(results_data.get("progress", 0.0))
                except Exception as e:
                    logger.warning(f"处理任务进度数据异常: {str(e)}")
                    # 错误时使用默认值0.0
                
                # 构建响应数据
                result.append({
                    "id": eval_task.id,
                    "name": eval_task.name or f"{eval_task.id}",  # 添加任务名称，如果为空则使用默认值
                    "model_name": eval_task.model_name,
                    "dataset_name": eval_task.dataset_name,
                    "status": eval_task.status.upper() if eval_task.status else "UNKNOWN",  # 确保状态大写
                    "progress": progress,
                    "created_at": eval_task.created_at,
                    "updated_at": eval_task.updated_at,
                    "task_id": eval_task.task_id
                })
            
            return result
        except Exception as e:
            logger.error(f"获取任务列表错误: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def get_evaluation_logs(self, eval_id: int, lines: Optional[int] = 50):
        """获取评估任务的实时日志
        
        Args:
            eval_id: 评估任务ID
            lines: 要获取的日志行数，默认50行
            
        Returns:
            List[str]: 日志行列表
        """
        # 先从Redis获取日志
        logs = RedisManager.get_logs(eval_id, max_lines=lines)
        
        if logs:
            return logs
        
        # 如果Redis中没有日志，尝试从运行器获取
        runner = get_runner(f"eval_{eval_id}")
        if runner:
            return runner.get_recent_logs(lines)
        
        # 最后尝试从文件获取
        try:
            BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
            logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
            log_pattern = f"eval_{eval_id}_*.log"
            
            log_files = list(Path(logs_dir).glob(log_pattern))
            if log_files:
                log_file = str(sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
                with open(log_file, 'r') as f:
                    all_lines = f.read().splitlines()
                    # 获取最后n行
                    log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                    
                    # 将日志添加到Redis
                    for line in log_lines:
                        RedisManager.append_log(eval_id, line)
                        
                    return log_lines
        except Exception as e:
            logger.warning(f"从文件读取日志失败: {str(e)}")
        
        # 如果没有运行中的任务，则返回空列表
        return []
    
    def terminate_evaluation(self, eval_id: int, db: Session):
        """终止评估任务
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 操作结果
        """
        # 检查任务是否存在
        eval_status = self.get_evaluation_status(eval_id, db)
        if eval_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"评估任务 {eval_id} 不存在"
            )
        
        # 尝试终止任务
        runner = get_runner(f"eval_{eval_id}")
        if runner and runner.is_running:
            success = runner.terminate()
            if success:
                # 更新数据库中的任务状态
                eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
                if eval_task:
                    eval_task.status = EvaluationStatus.TERMINATED.value
                    db.commit()
                    
                    # 更新 Redis 中的任务状态
                    try:
                        RedisManager.update_task_status(eval_id, {
                            "status": EvaluationStatus.TERMINATED.value,
                            "updated_at": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.warning(f"更新Redis任务状态失败: {str(e)}")
                
                return {"success": True, "message": "任务已终止"}
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="终止任务失败"
                )
        
        # 任务不在运行
        return {"success": False, "message": "任务不在运行状态"}
    
    def delete_evaluation(self, eval_id: int, db: Session):
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

def delete_evaluation(eval_id: int, db: Session):
    return evaluation_service.delete_evaluation(eval_id, db)

def update_evaluation_name(eval_id: int, name: str, db: Session):
    return evaluation_service.update_evaluation_name(eval_id, name, db)

# 为了WebSocket处理，导出服务实例
async def handle_websocket_logs(websocket: WebSocket, eval_id: int):
    """WebSocket日志处理的辅助函数
    
    Args:
        websocket: WebSocket连接
        eval_id: 评估任务ID
    """
    await evaluation_service.handle_websocket_logs(websocket, eval_id) 