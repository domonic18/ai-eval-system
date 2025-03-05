#!/usr/bin/env python3
"""
启动Celery Worker服务

处理后台任务的异步执行，包括模型评估任务
"""

import os
import sys
import importlib

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# 导入工具函数和日志模块
import logging
from datetime import datetime

# 显式导入任务模块以确保任务被注册
try:
    from apps.server.src.tasks import eval_tasks
    print("✅ 已加载评估任务模块")
except Exception as e:
    print(f"❌ 加载评估任务模块失败: {str(e)}")

try:
    from apps.server.src.tasks.celery_tasks import execute_evaluation_task
    print("✅ 已加载任务执行模块")
except Exception as e:
    print(f"❌ 加载任务执行模块失败: {str(e)}")

# 从apps.server导入celery应用
from apps.server.src.celery_app import celery_app

# 打印Celery Worker配置信息
print("\n=== Celery Worker配置 ===")
print(f"最大并发数: {celery_app.conf.worker_concurrency}")
print(f"默认队列: {celery_app.conf.task_default_queue}")
print(f"任务预取数: {celery_app.conf.worker_prefetch_multiplier}")
print(f"每个子进程最大任务数: {celery_app.conf.worker_max_tasks_per_child}")
print("========================\n")

# 列出已加载的任务
print("=== 已注册的任务 ===")
tasks = list(sorted(celery_app.tasks.keys()))
for task in tasks:
    if not task.startswith('celery.'):
        print(f"- {task}")
print("===================\n")

# 启动参数
worker_params = [
    'worker',
    f'--concurrency={celery_app.conf.worker_concurrency}',
    f'--prefetch-multiplier={celery_app.conf.worker_prefetch_multiplier}',
    f'--max-tasks-per-child={celery_app.conf.worker_max_tasks_per_child}',
    '--loglevel=INFO',
]

# 启动消息
print(f"[{datetime.now()}] 启动Celery Worker...")
print(f"执行命令: celery -A apps.server.src.celery_app {' '.join(worker_params)}")

# 启动Celery Worker
celery_app.worker_main(worker_params) 