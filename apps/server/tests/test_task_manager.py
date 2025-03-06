"""任务管理器测试模块

测试任务管理器的功能，包括任务创建、执行和状态管理
"""

import unittest
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
from datetime import datetime, timedelta
import threading

from apps.server.src.tasks.task_manager import TaskManager
from apps.server.src.tasks.task_status import TaskStatus
from apps.server.src.models.eval import EvaluationStatus


# 模拟TaskManager初始化方法，避免启动monitor_thread和加载现有任务
@patch('apps.server.src.tasks.task_manager.TaskManager._monitor_tasks')
@patch('apps.server.src.tasks.task_manager.TaskManager._load_existing_tasks')
class TestTaskManager(unittest.TestCase):
    """任务管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        # 重置TaskManager单例
        TaskManager._instance = None
        self.task_manager = TaskManager.get_instance()
        
        # 初始化活动任务集合
        self.task_manager.active_tasks = set()
    
    def tearDown(self):
        """测试后清理"""
        # 重置TaskManager单例
        TaskManager._instance = None
    
    def test_singleton_pattern(self, mock_load, mock_monitor):
        """测试单例模式"""
        # 获取两个实例
        manager1 = TaskManager.get_instance()
        manager2 = TaskManager.get_instance()
        
        # 验证是同一个实例
        self.assertIs(manager1, manager2)
    
    @patch('apps.server.src.tasks.task_manager.execute_evaluation_task')
    def test_create_task(self, mock_execute_task, mock_load, mock_monitor):
        """测试创建任务"""
        # 模拟Celery任务
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_execute_task.delay.return_value = mock_task
        
        # 模拟数据库会话
        mock_db = MagicMock()
        mock_evaluation = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_evaluation
        
        # 创建任务
        result = self.task_manager.create_task(1, mock_db)
        
        # 验证任务创建
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("task_id"), "test-task-id")
        self.assertIn(1, self.task_manager.tasks)
        self.assertEqual(self.task_manager.tasks[1]["status"], TaskStatus.QUEUED)
        
        # 验证Celery任务调用
        mock_execute_task.delay.assert_called_once()
    
    def test_get_task_status(self, mock_load, mock_monitor):
        """测试获取任务状态"""
        # 添加测试任务
        self.task_manager.tasks[1] = {
            "status": TaskStatus.RUNNING,
            "celery_id": "test-task-id",
            "eval_id": 100,
            "progress": 50
        }
        
        # 获取任务状态
        status = self.task_manager.get_task_status(1)
        
        # 验证状态
        self.assertEqual(status["status"], "RUNNING")
        self.assertEqual(status["db_status"], "running")
        self.assertEqual(status["progress"], 50)
    
    def test_update_task_status(self, mock_load, mock_monitor):
        """测试更新任务状态"""
        # 添加测试任务
        self.task_manager.tasks[1] = {
            "status": TaskStatus.RUNNING,
            "celery_id": "test-task-id",
            "eval_id": 100,
            "progress": 50
        }
        
        # 更新任务状态
        self.task_manager.update_task_status(1, TaskStatus.COMPLETED, {"progress": 100})
        
        # 验证状态更新
        self.assertEqual(self.task_manager.tasks[1]["status"], TaskStatus.COMPLETED)
        self.assertEqual(self.task_manager.tasks[1]["progress"], 100)
    
    @patch('apps.server.src.tasks.task_manager.get_celery_task_state')
    @patch('apps.server.src.tasks.task_manager.AsyncResult')
    @patch('apps.server.src.tasks.task_manager.get_runner')
    @patch('apps.server.src.tasks.task_manager.celery_app.control.revoke')
    def test_terminate_task(self, mock_revoke, mock_get_runner, mock_async_result, mock_get_state, mock_load, mock_monitor):
        """测试终止任务"""
        # 模拟Celery任务状态
        mock_get_state.return_value = "STARTED"
        
        # 模拟Runner
        mock_runner = MagicMock()
        mock_get_runner.return_value = mock_runner
        
        # 模拟AsyncResult
        mock_result = MagicMock()
        mock_async_result.return_value = mock_result
        
        # 添加测试任务
        self.task_manager.tasks[1] = {
            "status": TaskStatus.RUNNING,
            "celery_id": "test-task-id",
            "eval_id": 100,
            "progress": 50
        }
        self.task_manager.active_tasks.add(1)
        
        # 终止任务
        result = self.task_manager.terminate_task(1)
        
        # 验证任务终止
        self.assertTrue(result["success"])
        self.assertEqual(self.task_manager.tasks[1]["status"], TaskStatus.TERMINATED)
        mock_result.revoke.assert_called_once_with(terminate=True)
        mock_runner.terminate.assert_called_once()
    
    def test_clean_tasks(self, mock_load, mock_monitor):
        """测试清理过期任务"""
        # 设置当前时间
        now = datetime.now()
        old_time = now - timedelta(hours=48)  # 48小时前
        
        # 创建模拟任务
        # 1. 旧的已完成任务（应被清理）
        self.task_manager.tasks[1] = {
            "status": TaskStatus.COMPLETED,
            "celery_id": "test-task-id-1",
            "eval_id": 100,
            "progress": 100,
            "created_at": old_time,
            "updated_at": old_time
        }
        
        # 2. 旧的失败任务（应被清理）
        self.task_manager.tasks[2] = {
            "status": TaskStatus.FAILED,
            "celery_id": "test-task-id-2",
            "eval_id": 101,
            "progress": 75,
            "created_at": old_time,
            "updated_at": old_time
        }
        
        # 3. 运行中的任务（不应被清理）
        self.task_manager.tasks[3] = {
            "status": TaskStatus.RUNNING,
            "celery_id": "test-task-id-3",
            "eval_id": 102,
            "progress": 50,
            "created_at": old_time,
            "updated_at": now
        }
        
        # 新的已完成任务（不应被清理）
        self.task_manager.tasks[4] = {
            "status": TaskStatus.COMPLETED,
            "celery_id": "test-task-id-4",
            "eval_id": 103,
            "progress": 100,
            "created_at": now,
            "updated_at": now
        }
        
        # 映射Celery任务ID
        self.task_manager.celery_tasks = {
            "test-task-id-1": 1,
            "test-task-id-2": 2,
            "test-task-id-3": 3,
            "test-task-id-4": 4
        }
        
        # 清理任务
        cleaned_count = self.task_manager.clean_tasks()
        
        # 验证清理结果
        self.assertEqual(cleaned_count, 2)  # 应该清理了2个任务
        self.assertNotIn(1, self.task_manager.tasks)  # 旧的已完成任务应被清理
        self.assertNotIn(2, self.task_manager.tasks)  # 旧的失败任务应被清理
        self.assertIn(3, self.task_manager.tasks)     # 运行中的任务不应被清理
        self.assertIn(4, self.task_manager.tasks)     # 新的已完成任务不应被清理
        
        # 验证Celery任务ID映射也被清理
        self.assertNotIn("test-task-id-1", self.task_manager.celery_tasks)
        self.assertNotIn("test-task-id-2", self.task_manager.celery_tasks)
        self.assertIn("test-task-id-3", self.task_manager.celery_tasks)
        self.assertIn("test-task-id-4", self.task_manager.celery_tasks)
    
    def test_schedule_next_task(self, mock_load, mock_monitor):
        """测试调度下一个任务"""
        # 创建模拟数据库会话
        mock_db = MagicMock()
        mock_evaluation = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_evaluation
        
        # 模拟执行任务方法
        with patch.object(self.task_manager, '_execute_task') as mock_execute_task, \
             patch.object(self.task_manager, '_update_waiting_tasks') as mock_update_waiting_tasks:
            
            # 配置模拟方法的返回值
            mock_execute_task.return_value = {"success": True}
        
            # 模拟等待队列和活动任务
            self.task_manager.waiting_queue = MagicMock()
            self.task_manager.waiting_queue.popleft.return_value = 1
            self.task_manager.waiting_queue.__len__.return_value = 5
            self.task_manager.waiting_queue.__bool__.return_value = True
            
            # 模拟任务状态
            self.task_manager.tasks = {
                1: {"status": TaskStatus.WAITING, "eval_id": 1, "message": "等待中"}
            }
            
            # 调用调度方法
            result = self.task_manager._schedule_next_task(mock_db)
            
            # 验证结果
            self.assertTrue(result)
            
            # 验证任务执行方法被调用
            mock_execute_task.assert_called_once_with(1, mock_db)
            
            # 验证等待任务更新方法被调用
            mock_update_waiting_tasks.assert_called_once_with(mock_db)
            
            # 测试无等待任务情况
            self.task_manager.waiting_queue.__bool__.return_value = False
            
            result = self.task_manager._schedule_next_task(mock_db)
            self.assertFalse(result)
            
            # 测试活动任务已满情况
            self.task_manager.waiting_queue.__bool__.return_value = True
            self.task_manager.active_tasks = set(range(self.task_manager.max_concurrent_tasks))
            
            result = self.task_manager._schedule_next_task(mock_db)
            self.assertFalse(result)
    
    def test_update_waiting_tasks(self, mock_load, mock_monitor):
        """测试更新等待任务队列"""
        # 创建模拟数据库会话
        mock_db = MagicMock()
        mock_evaluations = [MagicMock() for _ in range(3)]
        
        def get_evaluation(Evaluation):  # 模拟filter参数
            class MockFilter:
                def filter(self, condition):
                    class MockFirst:
                        def first(self):
                            # 根据eval_id返回不同的模拟评估
                            eval_id = condition.right.value
                            return mock_evaluations[eval_id - 1]
                    return MockFirst()
            return MockFilter()
        
        # 使用with语句来限制测试范围并确保资源正确清理
        with patch.object(mock_db, 'query', get_evaluation):
            # 设置等待队列
            self.task_manager.waiting_queue = [1, 2, 3]
            
            # 调用更新方法
            self.task_manager._update_waiting_tasks(mock_db)
            
            # 验证每个等待任务的消息都已更新
            self.assertEqual(mock_evaluations[0].message, "任务等待中，前方队列任务数: 0")
            self.assertEqual(mock_evaluations[1].message, "任务等待中，前方队列任务数: 1")
            self.assertEqual(mock_evaluations[2].message, "任务等待中，前方队列任务数: 2")
            
            # 验证数据库提交被调用
            mock_db.commit.assert_called_once()
            
            # 测试异常处理
            mock_db.commit.side_effect = Exception("数据库错误")
            mock_db.rollback.reset_mock()  # 重置rollback调用计数
            
            # 调用更新方法，应捕获异常
            self.task_manager._update_waiting_tasks(mock_db)
            
            # 验证数据库回滚被调用
            mock_db.rollback.assert_called_once()
    
    @patch('apps.server.src.tasks.task_manager.execute_evaluation_task')
    def test_execute_task(self, mock_execute_task, mock_load, mock_monitor):
        """测试任务执行与数据库交互"""
        # 模拟Celery任务
        mock_task = MagicMock()
        mock_task.id = "test-execute-task-id"
        mock_execute_task.delay.return_value = mock_task
        
        # 模拟数据库会话和评估对象
        mock_db = MagicMock()
        mock_evaluation = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_evaluation
        
        # 使用with语句来限制测试范围并确保资源正确清理
        with patch.object(self.task_manager, '_schedule_next_task') as mock_schedule_next:
            # 准备测试任务
            eval_id = 100
            self.task_manager.tasks[eval_id] = {
                "status": TaskStatus.WAITING,
                "eval_id": eval_id,
                "message": "等待中",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 调用执行任务方法
            result = self.task_manager._execute_task(eval_id, mock_db)
            
            # 验证Celery任务调用
            mock_execute_task.delay.assert_called_once_with(None, eval_id)
            
            # 验证任务状态更新
            self.assertEqual(self.task_manager.tasks[eval_id]["status"], TaskStatus.QUEUED)
            self.assertEqual(self.task_manager.tasks[eval_id]["celery_id"], "test-execute-task-id")
            self.assertIn("任务已提交到执行队列", self.task_manager.tasks[eval_id]["message"])
            
            # 验证Celery任务映射更新
            self.assertEqual(self.task_manager.celery_tasks["test-execute-task-id"], eval_id)
            
            # 验证活动任务集合更新
            self.assertIn(eval_id, self.task_manager.active_tasks)
            
            # 验证数据库更新
            self.assertEqual(mock_evaluation.task_id, "test-execute-task-id")
            self.assertIn("任务已提交到执行队列", mock_evaluation.message)
            mock_db.commit.assert_called_once()
            
            # 验证返回结果
            self.assertTrue(result["success"])
            self.assertEqual(result["task_id"], "test-execute-task-id")
            self.assertEqual(result["status"], TaskStatus.QUEUED)
            
            # 测试异常情况
            mock_execute_task.reset_mock()
            mock_execute_task.delay.side_effect = Exception("Celery执行错误")
            mock_db.reset_mock()
            mock_evaluation.reset_mock()
            
            # 调用执行任务方法（应捕获异常）
            result = self.task_manager._execute_task(eval_id, mock_db)
            
            # 验证任务状态更新为失败
            self.assertEqual(self.task_manager.tasks[eval_id]["status"], TaskStatus.FAILED)
            self.assertIn("提交任务失败", self.task_manager.tasks[eval_id]["message"])
            self.assertIn("Celery执行错误", self.task_manager.tasks[eval_id]["error"])
            
            # 验证数据库更新（失败状态）
            self.assertEqual(mock_evaluation.status, EvaluationStatus.FAILED)
            self.assertIn("提交任务失败", mock_evaluation.message)
            
            # 验证尝试调度下一个任务
            mock_schedule_next.assert_called_once_with(mock_db)
            
            # 验证返回结果（失败）
            self.assertFalse(result["success"])


@pytest.mark.asyncio
@patch('apps.server.src.tasks.task_manager.TaskManager._monitor_tasks')
@patch('apps.server.src.tasks.task_manager.TaskManager._load_existing_tasks')
class TestAsyncTaskManager:
    """异步任务管理器测试"""
    
    async def setup_method(self, method):
        """测试前准备"""
        # 重置TaskManager单例
        TaskManager._instance = None
        self.task_manager = TaskManager.get_instance()
        
        # 初始化活动任务集合和任务锁
        self.task_manager.active_tasks = set()
        
        # 确保锁被初始化
        if not hasattr(self.task_manager, 'task_lock'):
            self.task_manager.task_lock = threading.Lock()
        if not hasattr(self.task_manager, 'scheduler_lock'):
            self.task_manager.scheduler_lock = threading.Lock()
    
    async def teardown_method(self, method):
        """测试后清理"""
        # 重置TaskManager单例
        TaskManager._instance = None
    
    @patch('apps.server.src.tasks.task_manager.execute_evaluation_task')
    async def test_async_task_execution(self, mock_execute_task, mock_load, mock_monitor):
        """测试异步任务执行"""
        # 模拟Celery任务
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_execute_task.delay.return_value = mock_task
        
        # 模拟数据库会话
        mock_db = MagicMock()
        mock_evaluation = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_evaluation
        
        # 创建多个任务
        tasks = []
        for i in range(5):
            result = self.task_manager.create_task(i, mock_db)
            tasks.append(result)
        
        # 验证任务创建
        assert len(self.task_manager.tasks) == 5
        assert len(self.task_manager.waiting_queue) == 4  # 第一个任务直接执行，其余4个在等待队列
        
        # 验证活动任务数
        assert len(self.task_manager.active_tasks) == 1
    
    @patch('apps.server.src.tasks.task_manager.execute_evaluation_task')
    async def test_async_db_interaction(self, mock_execute_task, mock_load, mock_monitor):
        """测试异步环境下的数据库交互"""
        # 模拟Celery任务
        mock_task = MagicMock()
        mock_task.id = "test-db-task-id"
        mock_execute_task.delay.return_value = mock_task
        
        # 模拟数据库会话
        mock_db = MagicMock()
        mock_evaluation = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_evaluation
        
        # 使用更好的隔离方式进行测试
        # 1. 测试任务创建与数据库交互
        result = self.task_manager.create_task(100, mock_db)
        
        # 验证数据库更新被调用
        mock_db.commit.assert_called_once()
        
        # 验证评估对象被更新
        assert mock_evaluation.status == EvaluationStatus.QUEUED.value
        
        # 重置mock以便后续测试
        mock_db.reset_mock()
        mock_evaluation.reset_mock()
        
        # 2. 测试任务状态更新
        with patch('apps.server.src.tasks.task_manager.SessionLocal') as mock_session:
            # 创建模拟会话和评估对象
            mock_session_instance = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            mock_eval = MagicMock()
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_eval
            
            # 模拟具有数据库连接的状态更新
            self.task_manager.update_task_status(100, TaskStatus.RUNNING, {"progress": 50})
            
            # 确保任务状态已更新
            assert self.task_manager.tasks[100]["status"] == TaskStatus.RUNNING
            assert self.task_manager.tasks[100]["progress"] == 50
            
            # 验证数据库更新
            assert mock_eval.status == EvaluationStatus.RUNNING.value
            mock_session_instance.commit.assert_called()
        
        # 3. 测试任务终止
        # 模拟AsyncResult和获取状态
        with patch('apps.server.src.tasks.task_manager.AsyncResult') as mock_async_result, \
             patch('apps.server.src.tasks.task_manager.get_celery_task_state') as mock_get_state, \
             patch('apps.server.src.tasks.task_manager.get_runner') as mock_get_runner, \
             patch('apps.server.src.tasks.task_manager.celery_app.control.revoke') as mock_revoke, \
             patch('apps.server.src.tasks.task_manager.SessionLocal') as mock_session:
            
            # 设置模拟返回值
            mock_get_state.return_value = "STARTED"
            mock_runner = MagicMock()
            mock_get_runner.return_value = mock_runner
            
            # 创建一个新的模拟数据库会话用于终止操作
            mock_term_db = MagicMock()
            mock_term_evaluation = MagicMock()
            mock_session.return_value.__enter__.return_value = mock_term_db
            mock_term_db.query.return_value.filter.return_value.first.return_value = mock_term_evaluation
            
            # 在任务对象中添加celery_id
            self.task_manager.tasks[100]["celery_id"] = "test-db-task-id"
            self.task_manager.celery_tasks["test-db-task-id"] = 100
            self.task_manager.active_tasks.add(100)  # 确保任务在活动集合中
            
            # 调用终止方法
            result = self.task_manager.terminate_task(100)
            
            # 验证终止结果
            assert result["success"] is True
            assert self.task_manager.tasks[100]["status"] == TaskStatus.TERMINATED
            
            # 验证数据库交互
            mock_term_db.commit.assert_called()
            assert mock_term_evaluation.status == EvaluationStatus.TERMINATED.value
            
            # 验证任务从活动集合中移除
            assert 100 not in self.task_manager.active_tasks
            
            # 验证Celery任务被撤销
            mock_revoke.assert_called_once()
            
            # 验证Runner的terminate方法被调用
            mock_runner.terminate.assert_called_once()


class TestTaskManagerCleanup(unittest.TestCase):
    """TaskManager清理功能测试"""
    
    def test_clean_tasks(self):
        """测试clean_tasks方法的独立功能"""
        # 创建TaskManager实例的模拟
        task_manager = MagicMock()
        
        # 创建测试数据
        now = datetime.now()
        old_time = now - timedelta(hours=25)  # 25小时前（超过默认的24小时）
        
        # 设置任务字典
        task_manager.tasks = {
            # 已完成的旧任务
            1: {
                "status": TaskStatus.COMPLETED,
                "celery_id": "test-task-id-1",
                "eval_id": 100,
                "progress": 100,
                "created_at": old_time,
                "updated_at": old_time
            },
            # 失败的旧任务
            2: {
                "status": TaskStatus.FAILED,
                "celery_id": "test-task-id-2",
                "eval_id": 101,
                "progress": 0,
                "created_at": old_time,
                "updated_at": old_time
            },
            # 运行中的任务（不应被清理）
            3: {
                "status": TaskStatus.RUNNING,
                "celery_id": "test-task-id-3",
                "eval_id": 102,
                "progress": 50,
                "created_at": old_time,
                "updated_at": old_time
            },
            # 新的已完成任务（不应被清理）
            4: {
                "status": TaskStatus.COMPLETED,
                "celery_id": "test-task-id-4",
                "eval_id": 103,
                "progress": 100,
                "created_at": now,
                "updated_at": now
            }
        }
        
        # 设置Celery任务映射
        task_manager.celery_tasks = {
            "test-task-id-1": 1,
            "test-task-id-2": 2,
            "test-task-id-3": 3,
            "test-task-id-4": 4
        }
        
        # 设置活动任务集合
        task_manager.active_tasks = set([1, 2, 3, 4])
        
        # 创建线程锁
        task_manager.task_lock = threading.Lock()
        
        # 获取clean_tasks方法的代码
        from apps.server.src.tasks.task_manager import TaskManager
        clean_tasks_method = TaskManager.clean_tasks
        
        # 在模拟对象上调用原始方法
        result = clean_tasks_method(task_manager)
        
        # 验证结果
        self.assertEqual(result, 2)  # 应该清理了2个任务
        self.assertNotIn(1, task_manager.tasks)  # 旧的已完成任务应被清理
        self.assertNotIn(2, task_manager.tasks)  # 旧的失败任务应被清理
        self.assertIn(3, task_manager.tasks)     # 运行中的任务不应被清理
        self.assertIn(4, task_manager.tasks)     # 新的已完成任务不应被清理
        
        # 验证Celery任务ID映射也被清理
        self.assertNotIn("test-task-id-1", task_manager.celery_tasks)
        self.assertNotIn("test-task-id-2", task_manager.celery_tasks)
        self.assertIn("test-task-id-3", task_manager.celery_tasks)
        self.assertIn("test-task-id-4", task_manager.celery_tasks)


if __name__ == "__main__":
    unittest.main() 