"""评估服务测试模块

测试评估服务的功能，包括任务创建、状态查询和终止
"""

import unittest
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import HTTPException, WebSocket
from sqlalchemy.orm import Session

from apps.server.src.services.eval_service import EvaluationService
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.tasks.task_manager import TaskManager
from apps.server.src.tasks.task_status import TaskStatus


class TestEvaluationService(unittest.TestCase):
    """评估服务测试"""
    
    def setUp(self):
        """测试前准备"""
        # 重置TaskManager单例
        TaskManager._instance = None
        # 创建评估服务实例
        self.eval_service = EvaluationService()
        # 模拟数据库会话
        self.mock_db = MagicMock(spec=Session)
    
    def tearDown(self):
        """测试后清理"""
        # 重置TaskManager单例
        TaskManager._instance = None
    
    @patch('apps.server.src.services.eval_service.TaskManager.get_instance')
    def test_create_evaluation_task(self, mock_get_instance):
        """测试创建评估任务"""
        # 模拟TaskManager
        mock_task_manager = MagicMock()
        mock_task_manager.create_task.return_value = "test-task-id"
        mock_get_instance.return_value = mock_task_manager
        
        # 模拟数据库操作
        mock_eval = MagicMock(spec=Evaluation)
        mock_eval.id = 1
        self.mock_db.add.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_db.refresh.return_value = None
        
        # 模拟Evaluation构造函数
        with patch('apps.server.src.services.eval_service.Evaluation') as mock_eval_class:
            mock_eval_class.return_value = mock_eval
            
            # 创建评估任务
            eval_data = {
                "model_name": "test-model",
                "dataset_name": "test-dataset",
                "model_configuration": {"param": "value"},
                "dataset_configuration": {"param": "value"}
            }
            result = self.eval_service.create_evaluation_task(eval_data, self.mock_db)
            
            # 验证结果
            self.assertEqual(result["id"], 1)
            self.assertEqual(result["task_id"], "test-task-id")
            
            # 验证数据库操作
            self.mock_db.add.assert_called_once()
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once_with(mock_eval)
            
            # 验证TaskManager调用
            mock_task_manager.create_task.assert_called_once_with(1, 1)
    
    @patch('apps.server.src.services.eval_service.TaskManager.get_instance')
    def test_get_evaluation_status(self, mock_get_instance):
        """测试获取评估状态"""
        # 模拟TaskManager
        mock_task_manager = MagicMock()
        mock_task_manager.get_task_status.return_value = {
            "status": "RUNNING",
            "db_status": "running",
            "progress": 50
        }
        mock_get_instance.return_value = mock_task_manager
        
        # 模拟数据库查询
        mock_eval = MagicMock(spec=Evaluation)
        mock_eval.id = 1
        mock_eval.status = EvaluationStatus.RUNNING.value
        mock_eval.progress = 50
        mock_eval.results = {"metric": "value"}
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_eval
        
        # 获取评估状态
        result = self.eval_service.get_evaluation_status(1, self.mock_db)
        
        # 验证结果
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["progress"], 50)
        self.assertEqual(result["results"], {"metric": "value"})
        
        # 验证TaskManager调用
        mock_task_manager.get_task_status.assert_called_once_with(1)
    
    @patch('apps.server.src.services.eval_service.TaskManager.get_instance')
    def test_terminate_evaluation(self, mock_get_instance):
        """测试终止评估任务"""
        # 模拟TaskManager
        mock_task_manager = MagicMock()
        mock_task_manager.terminate_task.return_value = True
        mock_get_instance.return_value = mock_task_manager
        
        # 模拟数据库查询
        mock_eval = MagicMock(spec=Evaluation)
        mock_eval.id = 1
        mock_eval.status = EvaluationStatus.RUNNING.value
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_eval
        
        # 终止评估任务
        result = self.eval_service.terminate_evaluation(1, self.mock_db)
        
        # 验证结果
        self.assertTrue(result)
        
        # 验证TaskManager调用
        mock_task_manager.terminate_task.assert_called_once_with(1)
        
        # 验证数据库更新
        self.assertEqual(mock_eval.status, EvaluationStatus.TERMINATED.value)
        self.mock_db.commit.assert_called_once()
    
    def test_list_evaluations(self):
        """测试列出评估任务"""
        # 模拟数据库查询
        mock_query = self.mock_db.query.return_value
        mock_filter = mock_query.filter.return_value if hasattr(mock_query, 'filter') else mock_query
        mock_order_by = mock_filter.order_by.return_value if hasattr(mock_filter, 'order_by') else mock_filter
        mock_offset = mock_order_by.offset.return_value if hasattr(mock_order_by, 'offset') else mock_order_by
        mock_limit = mock_offset.limit.return_value if hasattr(mock_offset, 'limit') else mock_offset
        
        # 模拟评估任务列表
        mock_eval1 = MagicMock(spec=Evaluation)
        mock_eval1.id = 1
        mock_eval1.name = "Test 1"
        mock_eval1.status = EvaluationStatus.COMPLETED.value
        
        mock_eval2 = MagicMock(spec=Evaluation)
        mock_eval2.id = 2
        mock_eval2.name = "Test 2"
        mock_eval2.status = EvaluationStatus.RUNNING.value
        
        mock_limit.all.return_value = [mock_eval1, mock_eval2]
        mock_query.count.return_value = 2
        
        # 列出评估任务
        result = self.eval_service.list_evaluations(None, 10, 0, self.mock_db)
        
        # 验证结果
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["items"][0]["id"], 1)
        self.assertEqual(result["items"][1]["id"], 2)


@pytest.mark.asyncio
class TestAsyncEvaluationService:
    """异步评估服务测试"""
    
    async def setup_method(self):
        """测试前准备"""
        # 重置TaskManager单例
        TaskManager._instance = None
        # 创建评估服务实例
        self.eval_service = EvaluationService()
    
    async def teardown_method(self):
        """测试后清理"""
        # 重置TaskManager单例
        TaskManager._instance = None
    
    @patch('apps.server.src.services.eval_service.RedisManager')
    async def test_register_websocket(self, mock_redis_manager):
        """测试注册WebSocket连接"""
        # 模拟WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_text = AsyncMock()
        
        # 模拟Redis操作
        mock_redis = MagicMock()
        mock_pubsub = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis_manager.get_instance.return_value = mock_redis
        
        # 模拟get_and_validate_evaluation
        with patch('apps.server.src.services.eval_service.get_and_validate_evaluation') as mock_get_eval:
            mock_eval = MagicMock(spec=Evaluation)
            mock_eval.id = 1
            mock_eval.status = EvaluationStatus.RUNNING.value
            mock_eval.progress = 50
            mock_get_eval.return_value = mock_eval
            
            # 模拟获取日志
            with patch('apps.server.src.services.eval_service.RedisManager.get_logs') as mock_get_logs:
                mock_get_logs.return_value = ["Log line 1", "Log line 2"]
                
                # 模拟websocket_context
                with patch('apps.server.src.services.eval_service.websocket_context') as mock_ws_context:
                    mock_ws_context.return_value.__aenter__.return_value = mock_websocket
                    mock_ws_context.return_value.__aexit__.return_value = None
                    
                    # 模拟pubsub_context
                    with patch('apps.server.src.services.eval_service.pubsub_context') as mock_pubsub_context:
                        mock_pubsub_context.return_value.__aenter__.return_value = mock_pubsub
                        mock_pubsub_context.return_value.__aexit__.return_value = None
                        
                        # 模拟pubsub.listen
                        mock_pubsub.listen.return_value = [
                            {"type": "message", "data": json.dumps({"log": "New log"})}
                        ]
                        
                        # 注册WebSocket连接
                        # 由于这是一个无限循环，我们需要模拟一个异常来退出
                        mock_websocket.receive_text.side_effect = [
                            '{"type": "ping"}',  # 第一次调用返回ping消息
                            Exception("Test exit")  # 第二次调用抛出异常以退出循环
                        ]
                        
                        try:
                            await self.eval_service.register_websocket(mock_websocket, 1)
                        except Exception as e:
                            if str(e) != "Test exit":
                                raise
                        
                        # 验证WebSocket操作
                        # 至少应该发送状态和日志
                        assert mock_websocket.send_text.call_count >= 2


if __name__ == "__main__":
    unittest.main() 