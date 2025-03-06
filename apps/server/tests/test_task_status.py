"""任务状态模块测试

测试task_status模块中的状态枚举和辅助函数
"""

import unittest
import pytest
from unittest.mock import patch, MagicMock

from apps.server.src.models.eval import EvaluationStatus
from apps.server.src.tasks.task_status import (
    TaskStatus,
    format_task_status,
    get_celery_task_state,
    map_celery_state_to_task_status
)


class TestTaskStatus(unittest.TestCase):
    """测试TaskStatus枚举和相关方法"""
    
    def test_from_evaluation_status(self):
        """测试从EvaluationStatus转换为TaskStatus"""
        # 测试正常转换
        self.assertEqual(TaskStatus.from_evaluation_status(EvaluationStatus.PENDING), TaskStatus.PENDING)
        self.assertEqual(TaskStatus.from_evaluation_status(EvaluationStatus.RUNNING), TaskStatus.RUNNING)
        self.assertEqual(TaskStatus.from_evaluation_status(EvaluationStatus.COMPLETED), TaskStatus.COMPLETED)
        self.assertEqual(TaskStatus.from_evaluation_status(EvaluationStatus.FAILED), TaskStatus.FAILED)
        self.assertEqual(TaskStatus.from_evaluation_status(EvaluationStatus.TERMINATED), TaskStatus.TERMINATED)
        
        # 测试未知状态转换
        mock_status = MagicMock()
        self.assertEqual(TaskStatus.from_evaluation_status(mock_status), TaskStatus.PENDING)
    
    def test_to_evaluation_status(self):
        """测试将TaskStatus转换为EvaluationStatus"""
        # 测试正常转换
        self.assertEqual(TaskStatus.PENDING.to_evaluation_status(), EvaluationStatus.PENDING)
        self.assertEqual(TaskStatus.WAITING.to_evaluation_status(), EvaluationStatus.PENDING)
        self.assertEqual(TaskStatus.QUEUED.to_evaluation_status(), EvaluationStatus.PENDING)
        self.assertEqual(TaskStatus.RUNNING.to_evaluation_status(), EvaluationStatus.RUNNING)
        self.assertEqual(TaskStatus.COMPLETED.to_evaluation_status(), EvaluationStatus.COMPLETED)
        self.assertEqual(TaskStatus.FAILED.to_evaluation_status(), EvaluationStatus.FAILED)
        self.assertEqual(TaskStatus.TERMINATED.to_evaluation_status(), EvaluationStatus.TERMINATED)


class TestTaskStatusHelpers(unittest.TestCase):
    """测试任务状态辅助函数"""
    
    def test_format_task_status(self):
        """测试格式化任务状态"""
        # 测试无元数据
        status_data = format_task_status(TaskStatus.RUNNING)
        self.assertEqual(status_data["status"], "RUNNING")
        self.assertEqual(status_data["db_status"], EvaluationStatus.RUNNING.value)
        
        # 测试有元数据
        metadata = {"message": "测试消息", "progress": 50}
        status_data = format_task_status(TaskStatus.RUNNING, metadata)
        self.assertEqual(status_data["status"], "RUNNING")
        self.assertEqual(status_data["db_status"], EvaluationStatus.RUNNING.value)
        self.assertEqual(status_data["message"], "测试消息")
        self.assertEqual(status_data["progress"], 50)
    
    def test_get_celery_task_state(self):
        """测试获取Celery任务状态"""
        # 模拟AsyncResult
        mock_task = MagicMock()
        mock_task.state = "SUCCESS"
        
        # 替换AsyncResult
        with patch('apps.server.src.tasks.task_status.AsyncResult', return_value=mock_task):
            state = get_celery_task_state("test-task-id")
            self.assertEqual(state, "SUCCESS")
        
        # 测试异常情况
        with patch('apps.server.src.tasks.task_status.AsyncResult', side_effect=Exception("测试异常")):
            state = get_celery_task_state("test-task-id")
            self.assertIsNone(state)
    
    def test_map_celery_state_to_task_status(self):
        """测试将Celery状态映射为TaskStatus"""
        # 测试各种状态映射
        self.assertEqual(map_celery_state_to_task_status('PENDING'), TaskStatus.PENDING)
        self.assertEqual(map_celery_state_to_task_status('STARTED'), TaskStatus.RUNNING)
        self.assertEqual(map_celery_state_to_task_status('RETRY'), TaskStatus.RUNNING)
        self.assertEqual(map_celery_state_to_task_status('SUCCESS'), TaskStatus.COMPLETED)
        self.assertEqual(map_celery_state_to_task_status('FAILURE'), TaskStatus.FAILED)
        self.assertEqual(map_celery_state_to_task_status('REVOKED'), TaskStatus.TERMINATED)
        
        # 测试未知状态
        self.assertEqual(map_celery_state_to_task_status('UNKNOWN'), TaskStatus.PENDING)


if __name__ == "__main__":
    unittest.main() 