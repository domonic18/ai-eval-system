from celery import Celery
from dotenv import load_dotenv
from apps.server.src.core.config import REDIS_URL, APP_NAME, settings
import os

load_dotenv()

# Celery应用实例
celery_app = Celery(
    f"{settings.app_name.lower().replace(' ', '_')}_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "apps.server.src.tasks.eval_tasks",
        "apps.server.src.tasks.celery_tasks"  # 添加celery_tasks模块确保execute_evaluation_task被注册
    ]
)

# 添加自动发现任务
celery_app.autodiscover_tasks(["apps.server.src.tasks"])

# Celery配置
celery_app.conf.update(
    # 序列化和内容设置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区设置
    timezone="Asia/Shanghai",
    enable_utc=False,
    
    # 任务跟踪和事件设置
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # 默认队列
    task_default_queue='eval_tasks',
    
    # 限制并发任务数量为2
    worker_concurrency=2,
    
    # 预取设置 - 限制worker预取的任务数量
    worker_prefetch_multiplier=1,
    
    # 设置最大任务量，执行指定数量的任务后重启worker
    worker_max_tasks_per_child=10
)

# 添加调试配置
if settings.debug:
    celery_app.conf.update(
        # task_always_eager=True,  # 同步模式方便调试
        task_eager_propagates=True,
        worker_redirect_stdouts=False
    )