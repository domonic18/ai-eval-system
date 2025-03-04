from celery import Celery
from dotenv import load_dotenv
from apps.server.src.core.config import REDIS_URL, APP_NAME, settings
import os

load_dotenv()

# 开发环境使用内存作为broker和backend
celery_app = Celery(
    f"{settings.app_name.lower().replace(' ', '_')}_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["apps.server.src.tasks.eval_tasks"]
)

# 添加自动发现任务
celery_app.autodiscover_tasks(["apps.server.src.tasks"])

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_default_queue='eval_tasks'
)

# 添加调试配置
if settings.debug:
    celery_app.conf.update(
        # task_always_eager=True,  # 同步模式方便调试
        task_eager_propagates=True,
        worker_redirect_stdouts=False
    ) 