from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

# 开发环境使用内存作为broker和backend
celery_app = Celery(
    "ai_eval_tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
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