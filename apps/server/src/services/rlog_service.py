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
        pass
    
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
                    
                    # 新增：提取log字段内容
                    try:
                        import json
                        log_data = json.loads(data)
                        log_content = log_data.get("log", data)  # 如果解析失败则回退到原始数据
                    except json.JSONDecodeError:
                        log_content = data  # 非JSON格式则直接使用原始数据
                    
                    # 发送到WebSocket
                    await websocket.send_text(log_content)
                    
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
    