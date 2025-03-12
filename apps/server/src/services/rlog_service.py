import logging
import traceback
import asyncio
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from utils.redis_manager import RedisManager


# 日志配置
logger = logging.getLogger(__name__)


class WebSocketLogService:
    """WebSocket日志服务"""

    def __init__(self):
        # 存储活动连接的后台任务，用于清理
        self.active_tasks = {}
    
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
        background_task = None
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
            
            # 5. 创建后台任务来处理日志消息，而不是直接调用
            background_task = asyncio.create_task(
                self._listen_for_log_messages(websocket, pubsub, client_id, eval_id)
            )
            
            # 存储后台任务引用以便清理
            self.active_tasks[client_id] = {
                "task": background_task,
                "heartbeat": heartbeat_task,
                "eval_id": eval_id,
                "pubsub": pubsub,
                "redis_client": redis_client
            }
            
            # 等待连接关闭
            await self._wait_for_disconnect(websocket, client_id)
            
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
            # 清理资源
            await self._cleanup_connection(client_id, pubsub, redis_client, websocket)

    async def _wait_for_disconnect(self, websocket: WebSocket, client_id: str):
        """等待WebSocket连接断开
        
        Args:
            websocket: WebSocket连接
            client_id: 客户端ID
        """
        try:
            # 等待从客户端接收消息，如果客户端断开连接，这里会引发WebSocketDisconnect异常
            while True:
                message = await websocket.receive_text()
                logger.debug(f"收到来自客户端的消息: {message[:100]}...")
        except WebSocketDisconnect:
            logger.info(f"客户端断开连接 [client_id={client_id}]")
            raise

    async def _cleanup_connection(self, client_id: str, pubsub=None, redis_client=None, websocket=None):
        """清理连接资源
        
        Args:
            client_id: 客户端ID
            pubsub: Redis PubSub对象
            redis_client: Redis客户端
            websocket: WebSocket连接
        """
        # 获取并取消后台任务
        task_info = self.active_tasks.pop(client_id, None)
        if task_info:
            background_task = task_info.get("task")
            heartbeat_task = task_info.get("heartbeat")
            
            # 取消后台日志监听任务
            if background_task and not background_task.done():
                background_task.cancel()
                try:
                    await background_task
                except asyncio.CancelledError:
                    logger.debug(f"后台日志任务已取消 [client_id={client_id}]")
                except Exception as e:
                    logger.warning(f"取消后台任务时出错: {str(e)}")
            
            # 取消心跳任务
            if heartbeat_task and not heartbeat_task.done():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    logger.debug(f"心跳任务已取消 [client_id={client_id}]")
                except Exception as e:
                    logger.warning(f"取消心跳任务时出错: {str(e)}")
        
        # 清理Redis资源
        await self._cleanup_websocket_resources(pubsub, redis_client)
        
        # 关闭WebSocket连接
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"关闭WebSocket连接失败: {str(e)}")
        
        logger.info(f"WebSocket连接资源已清理 [client_id={client_id}]")

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

    async def _listen_for_log_messages(self, websocket: WebSocket, pubsub, client_id: str, eval_id: int):
        """监听Redis日志消息并转发到WebSocket
        
        Args:
            websocket: WebSocket连接
            pubsub: Redis PubSub对象
            client_id: 客户端唯一标识
            eval_id: 评估任务ID
        """
        logger.debug(f"开始监听Redis日志消息 [client_id={client_id}, eval_id={eval_id}]")
        
        # 添加超时控制，防止任务无限运行
        max_idle_time = 3600  # 最大空闲时间（秒）
        last_message_time = asyncio.get_event_loop().time()
        
        try:
            while True:
                # 1. 检查WebSocket连接状态
                if websocket.client_state != WebSocketState.CONNECTED:
                    logger.debug(f"WebSocket连接已断开，停止监听 [client_id={client_id}]")
                    break
                
                # 2. 检查超时 - 长时间没有消息时自动断开
                current_time = asyncio.get_event_loop().time()
                if current_time - last_message_time > max_idle_time:
                    logger.warning(f"日志监听超时，停止监听 [client_id={client_id}]")
                    break
                
                try:
                    # 3. 非阻塞方式获取消息
                    message = pubsub.get_message(timeout=0.1)
                    
                    # 4. 处理消息
                    if message and message["type"] == "message":
                        # 更新最后收到消息的时间
                        last_message_time = asyncio.get_event_loop().time()
                        
                        # 解析消息内容
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        
                        # 提取log字段内容
                        try:
                            import json
                            log_data = json.loads(data)
                            log_content = log_data.get("log", data)  # 如果解析失败则回退到原始数据
                        except json.JSONDecodeError:
                            log_content = data  # 非JSON格式则直接使用原始数据
                        
                        # 发送到WebSocket
                        await websocket.send_text(log_content)
                    
                    # 5. 短暂休眠，避免CPU占用过高，同时也使任务可被取消
                    await asyncio.sleep(0.01)
                    
                except asyncio.CancelledError:
                    logger.info(f"日志监听任务被取消 [client_id={client_id}]")
                    raise
                except Exception as e:
                    logger.warning(f"处理Redis消息失败: {str(e)}")
                    if "connection closed" in str(e).lower() or "close message has been sent" in str(e).lower():
                        break
                    # 短暂停顿后继续尝试
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info(f"日志监听任务被取消 [client_id={client_id}]")
            raise
        except Exception as e:
            logger.error(f"日志监听异常 [client_id={client_id}]: {str(e)}")
        finally:
            logger.info(f"日志监听任务结束 [client_id={client_id}]")

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
    