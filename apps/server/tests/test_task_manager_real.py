"""TaskManager真实环境集成测试

这个测试模块不使用mock，而是在真实环境中测试TaskManager的完整流程。
"""

import unittest
import pytest
import time
import threading
from datetime import datetime, timedelta
import logging
import sys
import os

# 确保日志配置正确
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

from apps.server.src.tasks.task_manager import TaskManager
from apps.server.src.tasks.task_status import TaskStatus
from apps.server.src.models.eval import EvaluationStatus, Evaluation
from apps.server.src.db import SessionLocal, engine, Base

class TestTaskManagerRealFlow(unittest.TestCase):
    """TaskManager真实环境集成测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化前的准备工作"""
        # 创建测试用的数据库表
        Base.metadata.create_all(bind=engine)
        
        # 确保TaskManager单例已重置
        TaskManager._instance = None
        
        # 创建一个带标识的测试任务管理器
        cls.task_manager = TaskManager.get_instance()
        cls.task_manager.is_test_instance = True  # 标记为测试实例
        
        # 设置较短的清理周期，方便测试
        cls.original_clean_interval = TaskManager.CLEAN_INTERVAL_MINUTES
        TaskManager.CLEAN_INTERVAL_MINUTES = 1
        
        # 设置较短的监控间隔
        cls.original_monitor_interval = 60  # 假设原始值为60秒
        if hasattr(cls.task_manager, '_monitor_interval'):
            cls.original_monitor_interval = cls.task_manager._monitor_interval
            cls.task_manager._monitor_interval = 2  # 设置为2秒
    
    @classmethod
    def tearDownClass(cls):
        """测试类结束后的清理工作"""
        # 恢复原始设置
        TaskManager.CLEAN_INTERVAL_MINUTES = cls.original_clean_interval
        if hasattr(cls.task_manager, '_monitor_interval'):
            cls.task_manager._monitor_interval = cls.original_monitor_interval
        
        # 停止监控线程
        if hasattr(cls.task_manager, 'monitor_thread') and cls.task_manager.monitor_thread.is_alive():
            cls.task_manager._should_stop = True
            cls.task_manager.monitor_thread.join(timeout=5)
            if cls.task_manager.monitor_thread.is_alive():
                logging.warning("监控线程未能在超时时间内正常停止")
        
        # 清理测试任务
        with SessionLocal() as db:
            # 删除测试期间创建的评估记录
            db.query(Evaluation).filter(Evaluation.id >= 9000).delete()
            db.commit()
        
        # 重置TaskManager单例
        TaskManager._instance = None
    
    def setUp(self):
        """每个测试方法前的准备工作"""
        # 创建测试用的数据库会话
        self.db = SessionLocal()
        
        # 清理之前测试可能留下的任务
        self.task_manager.tasks.clear()
        self.task_manager.celery_tasks.clear()
        self.task_manager.active_tasks.clear()
        if hasattr(self.task_manager, 'waiting_queue'):
            self.task_manager.waiting_queue.clear()
    
    def tearDown(self):
        """每个测试方法后的清理工作"""
        # 关闭数据库会话
        self.db.close()
    
    def _create_test_evaluation(self, status=EvaluationStatus.PENDING):
        """创建一个用于测试的评估记录"""
        # 使用9000以上的ID，以便于识别测试数据
        test_id = int(time.time() * 100) % 1000 + 9000
        
        evaluation = Evaluation(
            id=test_id,
            user_id=1,
            name=f"Test Evaluation {test_id}",
            model="hk33smarter_api",
            dataset="demo_cmmlu_chat_gen",
            status=status.value,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            config={"test": True}
        )
        
        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)
        
        return evaluation
    
    def test_task_creation_and_execution(self):
        """测试任务创建和执行的完整流程"""
        # 创建测试评估记录
        evaluation = self._create_test_evaluation()
        
        # 创建任务
        result = self.task_manager.create_task(evaluation.id, self.db)
        
        # 验证任务创建成功
        self.assertTrue(result.get("success", False))
        self.assertIn(evaluation.id, self.task_manager.tasks)
        
        # 等待任务被调度和执行
        max_wait = 10  # 最多等待10秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # 获取最新状态
            task_info = self.task_manager.get_task_status(evaluation.id)
            
            # 如果状态已经更新（不再是PENDING/QUEUED），则测试通过
            if task_info.get("status") not in ["PENDING", "QUEUED", "WAITING"]:
                break
            
            time.sleep(0.5)
        
        # 验证任务状态已更新
        self.assertNotIn(task_info.get("status"), ["PENDING", "QUEUED", "WAITING"])
        
        # 验证数据库状态也已更新
        self.db.refresh(evaluation)
        self.assertNotEqual(evaluation.status, EvaluationStatus.PENDING.value)
    
    def test_multiple_task_scheduling(self):
        """测试多任务调度和队列管理"""
        # 设置最大并发任务数
        original_max_concurrent = self.task_manager.max_concurrent_tasks
        self.task_manager.max_concurrent_tasks = 2
        
        try:
            # 创建5个测试评估记录
            evaluations = []
            for _ in range(5):
                evaluation = self._create_test_evaluation()
                evaluations.append(evaluation)
            
            # 创建5个任务
            for evaluation in evaluations:
                result = self.task_manager.create_task(evaluation.id, self.db)
                self.assertTrue(result.get("success", False))
            
            # 验证只有2个任务在活动集合中（其他在等待队列）
            self.assertEqual(len(self.task_manager.active_tasks), 2)
            
            # 验证等待队列中有3个任务
            if hasattr(self.task_manager, 'waiting_queue'):
                self.assertEqual(len(self.task_manager.waiting_queue), 3)
            
            # 等待一段时间，让监控线程执行
            time.sleep(5)
            
            # 验证任务状态
            active_count = 0
            waiting_count = 0
            for eval_id in [e.id for e in evaluations]:
                status = self.task_manager.get_task_status(eval_id)
                if status.get("status") in ["RUNNING", "QUEUED"]:
                    active_count += 1
                elif status.get("status") == "WAITING":
                    waiting_count += 1
            
            # 验证活动任务不超过最大并发数
            self.assertLessEqual(active_count, self.task_manager.max_concurrent_tasks)
            
        finally:
            # 恢复原始设置
            self.task_manager.max_concurrent_tasks = original_max_concurrent
    
    def test_task_cleanup(self):
        """测试任务自动清理功能"""
        # 创建一个旧的完成任务
        old_evaluation = self._create_test_evaluation(status=EvaluationStatus.COMPLETED)
        
        # 手动添加到任务管理器，并设置为旧时间
        old_time = datetime.now() - timedelta(hours=25)  # 超过默认的24小时清理阈值
        
        self.task_manager.tasks[old_evaluation.id] = {
            "status": TaskStatus.COMPLETED,
            "celery_id": f"test-celery-{old_evaluation.id}",
            "eval_id": old_evaluation.id,
            "progress": 100,
            "created_at": old_time,
            "updated_at": old_time
        }
        
        # 添加Celery任务映射
        self.task_manager.celery_tasks[f"test-celery-{old_evaluation.id}"] = old_evaluation.id
        
        # 创建一个新的完成任务
        new_evaluation = self._create_test_evaluation(status=EvaluationStatus.COMPLETED)
        
        # 手动添加到任务管理器
        new_time = datetime.now()
        
        self.task_manager.tasks[new_evaluation.id] = {
            "status": TaskStatus.COMPLETED,
            "celery_id": f"test-celery-{new_evaluation.id}",
            "eval_id": new_evaluation.id,
            "progress": 100,
            "created_at": new_time,
            "updated_at": new_time
        }
        
        # 添加Celery任务映射
        self.task_manager.celery_tasks[f"test-celery-{new_evaluation.id}"] = new_evaluation.id
        
        # 手动触发清理
        cleaned_count = self.task_manager.clean_tasks()
        
        # 验证旧任务被清理
        self.assertEqual(cleaned_count, 1)
        self.assertNotIn(old_evaluation.id, self.task_manager.tasks)
        self.assertNotIn(f"test-celery-{old_evaluation.id}", self.task_manager.celery_tasks)
        
        # 验证新任务未被清理
        self.assertIn(new_evaluation.id, self.task_manager.tasks)
        self.assertIn(f"test-celery-{new_evaluation.id}", self.task_manager.celery_tasks)
    
    def test_terminate_task(self):
        """测试任务终止功能"""
        # 创建测试评估记录
        evaluation = self._create_test_evaluation()
        
        # 创建任务
        result = self.task_manager.create_task(evaluation.id, self.db)
        self.assertTrue(result.get("success", False))
        
        # 等待任务进入运行状态
        time.sleep(2)
        
        # 终止任务
        terminate_result = self.task_manager.terminate_task(evaluation.id)
        
        # 验证终止结果
        self.assertTrue(terminate_result.get("success", False))
        
        # 获取任务状态
        status = self.task_manager.get_task_status(evaluation.id)
        
        # 验证任务状态已更新为终止
        self.assertEqual(status.get("status"), "TERMINATED")
        
        # 验证数据库状态也已更新
        self.db.refresh(evaluation)
        self.assertEqual(evaluation.status, EvaluationStatus.TERMINATED.value)
        
        # 验证任务已从活动集合中移除
        self.assertNotIn(evaluation.id, self.task_manager.active_tasks)


if __name__ == "__main__":
    unittest.main() 