from celery import Celery
from dotenv import load_dotenv
from core.config import settings
import os

load_dotenv()

# 开发环境使用内存作为broker和backend
celery_app = Celery(
    f"{settings.APP_NAME.lower().replace(' ', '_')}_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.task_eval"]  # 明确包含任务模块
)

celery_app.conf.task_routes = {
    'tasks.task_eval.*': {'queue': 'eval_tasks'}
}   

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

    # 限制并发任务数量
    task_acks_late=True,                  # 任务完成后确认
    worker_prefetch_multiplier=1,         # 严格并发控制
    worker_concurrency=1,                 # 单worker模式
    worker_max_tasks_per_child=1,         # 每个进程只处理一个任务
    task_concurrency=1,                    # 全局并发限制

    # 失败重试机制
    task_reject_on_worker_lost=True, # worker失败时放回队列
    task_acks_on_failure_or_timeout=False, # 失败不确认，重新入队
)

# 添加调试配置
# if settings.DEBUG:
#     celery_app.conf.update(
#         # task_always_eager=True,  # 同步模式方便调试
#         task_eager_propagates=True,
#         worker_redirect_stdouts=False
#     )

# 添加健康检查路由
@celery_app.task(name="health_check")
def health_check():
    return {"status": "ok"}
