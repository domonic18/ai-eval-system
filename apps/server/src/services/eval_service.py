from fastapi import Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from apps.server.src.db import get_db, SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from celery.result import AsyncResult
import traceback
from typing import Optional, Union, Iterator, Dict, Any, List
import logging
import json
from pathlib import Path
from apps.server.src.tasks.eval_tasks import run_evaluation
from apps.server.src.utils.redis_manager import RedisManager
from apps.server.src.tasks.opencompass_runner import get_runner
from datetime import datetime
import os

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
        db_session = None
        close_db = False
        
        try:
            # 使用FastAPI的依赖注入处理db对象
            if db is not None:
                # 直接使用提供的会话，不需要额外处理
                db_session = db
            else:
                # 如果没有提供会话，创建一个新的
                from apps.server.src.db import SessionLocal
                db_session = SessionLocal()
                close_db = True
            
            # 验证输入数据
            if not eval_data.model_name:
                raise ValueError("模型名称不能为空")
            if not eval_data.dataset_name:
                raise ValueError("数据集名称不能为空")
            
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
            try:
                log_dir = Path(f"logs/eval_{db_eval.id}")
                log_dir.mkdir(parents=True, exist_ok=True)
                
                # 更新日志目录
                db_eval.log_dir = str(log_dir)
                db_session.commit()
            except Exception as log_dir_error:
                logger.warning(f"创建日志目录失败: {str(log_dir_error)}")
                # 不中断流程，继续执行
            
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
            if db_session:
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
            # 确保在使用完毕后关闭数据库会话
            if close_db and db_session is not None:
                db_session.close()

    async def get_evaluation_status(self, eval_id: int, db: Session):
        """获取评估任务状态
        
        Args:
            eval_id: 评估任务ID
            db: 数据库会话
            
        Returns:
            Optional[EvaluationStatusResponse]: 评估任务状态
        """
        # 处理db可能是生成器的情况（FastAPI依赖注入）
        db_session = None
        close_session = False
        
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
            
            # 使用FastAPI的依赖注入处理db对象
            if db is not None:
                # 直接使用提供的会话，不需要额外处理
                db_session = db
            else:
                # 如果没有提供会话，创建一个新的
                from apps.server.src.db import SessionLocal
                db_session = SessionLocal()
                close_session = True
            
            # 查询数据库
            eval_task = db_session.query(Evaluation).filter(Evaluation.id == eval_id).first()
            if not eval_task:
                return None
            
            # 构建基本响应对象(安全处理字段)
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
        
        finally:
            # 确保在使用完毕后关闭数据库会话
            if close_session and db_session is not None:
                db_session.close()
                logger.debug(f"关闭数据库会话 (eval_id={eval_id})")

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
            pubsub, redis = await self._subscribe_to_log_channel(websocket, eval_id)
            
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
        """发送历史日志记录
        
        Args:
            websocket: WebSocket连接
            eval_id: 评估任务ID
        """
        # 先获取Redis中现有的日志
        existing_logs = RedisManager.get_logs(eval_id, max_lines=200)
        if existing_logs:
            await websocket.send_json({"info": f"已加载{len(existing_logs)}条历史日志"})
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
                        for line in lines[-200:]:
                            # 添加到Redis并发送
                            RedisManager.append_log(eval_id, line)
                            await websocket.send_text(line)
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
            redis = await RedisManager.get_async_instance()
            channel = RedisManager.get_log_channel(eval_id)
            
            # 订阅频道
            pubsub = redis.pubsub()
            await pubsub.subscribe(channel)
            
            # 发送初始连接成功消息
            await websocket.send_json({"info": f"已连接到任务 {eval_id} 的日志订阅"})
            
            return pubsub, redis
        except Exception as redis_error:
            logger.error(f"Redis订阅错误: {str(redis_error)}")
            await websocket.send_json({"error": f"日志订阅出错: {str(redis_error)}"})
            return None, None
    
    async def _listen_for_log_messages(self, websocket: WebSocket, pubsub):
        """监听Redis日志消息并转发到WebSocket
        
        Args:
            websocket: WebSocket连接
            pubsub: Redis PubSub对象
        """
        async for message in pubsub.listen():
            if message["type"] == "message":
                log_line = message["data"]
                if isinstance(log_line, bytes):
                    log_line = log_line.decode('utf-8')
                await websocket.send_text(log_line)
                
            # 定期检查WebSocket连接状态
            if not websocket.client_state.CONNECTED:
                break
    
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

# 创建服务实例
evaluation_service = EvaluationService()

# 为了向后兼容，保留原来的函数
async def create_evaluation_task(eval_data, db: Union[Session, Iterator[Session]] = Depends(get_db)):
    return await evaluation_service.create_evaluation_task(eval_data, db)

async def get_evaluation_status(eval_id: int, db: Session):
    return await evaluation_service.get_evaluation_status(eval_id, db)

# 为了WebSocket处理，导出服务实例
async def handle_websocket_logs(websocket: WebSocket, eval_id: int):
    """WebSocket日志处理的辅助函数
    
    Args:
        websocket: WebSocket连接
        eval_id: 评估任务ID
    """
    await evaluation_service.handle_websocket_logs(websocket, eval_id) 