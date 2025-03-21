import logging
import contextlib
from celery_app import celery_app
from core.database import SessionLocal
from tasks.task_evaluator import TaskEvaluator


# 配置日志
logger = logging.getLogger("eval_tasks")
logger.setLevel(logging.DEBUG)


# @contextlib.contextmanager
# def db_session():
#     """数据库会话上下文管理器
    
#     使用示例:
#     with db_session() as db:
#         # 使用数据库会话db
#     """
#     session = SessionLocal()
#     try:
#         yield session
#     finally:
#         session.close()

# def with_db_session(func):
#     """数据库会话装饰器
    
#     自动管理函数中的数据库会话资源
#     """
#     def wrapper(*args, **kwargs):
#         with db_session() as session:
#             # 将db会话作为第一个参数传入
#             return func(session, *args, **kwargs)
#     return wrapper

@celery_app.task(bind=True, name='task_eval.run_evaluation', queue='eval_tasks')
def run_evaluation(self, eval_id: int):
    """
    运行评估任务

    Args:
        eval_id: 评估任务ID
        
    Returns:
        dict: 任务状态信息
    """
    evaluator = TaskEvaluator(self, eval_id)
    return evaluator.execute_sync()
