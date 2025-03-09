# # import os
# # import json
# # import time
# # import logging
# # import threading
# # import contextlib
# # from datetime import datetime
# # from celery import shared_task
# # from sqlalchemy import update
# # from sqlalchemy.orm import Session
# # from core.celery_app import celery_app
# # from core.database import SessionLocal
# # from models.eval import Evaluation, EvaluationStatus
# # from core.config import OPENCOMPASS_PATH
# # from pathlib import Path
# from tasks.runners.runner_opencompas import OpenCompassRunner, create_runner, get_runner, remove_runner
# from utils.redis_manager import RedisManager
# from tasks.task_evaluator import TaskEvaluator


# # 使用相对于项目根目录的绝对路径
# BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
# print(f"OpenCompass路径: {OPENCOMPASS_PATH}")

# # 配置日志
# logger = logging.getLogger("eval_tasks")
# logger.setLevel(logging.DEBUG)

# # 确保日志目录存在
# log_dir = os.path.join(BASE_DIR, "logs")
# os.makedirs(log_dir, exist_ok=True)

# # 添加文件处理器
# file_handler = logging.FileHandler(os.path.join(log_dir, "eval_tasks.log"))
# file_handler.setLevel(logging.DEBUG)

# # 添加控制台处理器
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.INFO)

# # 设置格式
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(formatter)
# console_handler.setFormatter(formatter)

# # 添加处理器到日志记录器
# if not logger.handlers:
#     logger.addHandler(file_handler)
#     logger.addHandler(console_handler)

# # 跟踪活动的任务和监控线程
# _active_tasks = {}

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

# def handle_task_status_update(status_dict):
#     """处理任务状态更新的回调函数
    
#     当OpenCompassRunner状态变更时会调用此函数
    
#     Args:
#         status_dict: 包含状态信息的字典
#     """
#     # 获取任务ID，假设已在runner初始化时设置
#     task_id = int(status_dict.get('task_id', -1))
#     if task_id == -1:
#         logger.warning(f"收到状态更新回调，但缺少task_id: {status_dict}")
#         return
        
#     # 提取状态信息并更新数据库
#     try:
#         with db_session() as db:
#             # 如果状态含有progress，则更新进度
#             if 'progress' in status_dict:
#                 update_task_progress(db, task_id, status_dict['progress'])
                
#             # 如果状态中含有完成标志，则更新任务状态
#             if status_dict.get('status') == 'finished':
#                 is_successful = status_dict.get('is_successful', False)
#                 if is_successful:
#                     update_task_status(db, task_id, EvaluationStatus.COMPLETED)
#                 else:
#                     error_msg = status_dict.get('error_message', '未知错误')
#                     update_task_error(db, task_id, error_msg)
#                     update_task_status(db, task_id, EvaluationStatus.FAILED)
#     except Exception as e:
#         logger.error(f"处理状态更新回调时出错: {str(e)}")

# @celery_app.task(bind=True, name='eval_task.run_evaluation', queue='eval_tasks')
# def run_evaluation(self, eval_id: int):
#     """
#     运行评估任务

#     Args:
#         eval_id: 评估任务ID
        
#     Returns:
#         dict: 任务状态信息
#     """
#     # 创建任务执行器并执行任务
#     # evaluator = TaskEvaluator(self, eval_id)
#     # return evaluator.execute()

# def update_task_status(db: Session, eval_id: int, status: EvaluationStatus, results=None):
#     """更新任务状态
    
#     Args:
#         db: 数据库会话
#         eval_id: 评估任务ID
#         status: 任务状态
#         results: 可选的任务结果
#     """
#     eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
#     if eval_task:
#         eval_task.status = status
#         if results:
#             eval_task.results = results
#         db.commit()
        
#         # 通过Redis更新任务状态
#         try:
#             RedisManager.update_task_status(eval_id, {
#                 "status": status.value,
#                 "updated_at": datetime.now().isoformat()
#             })
#             logger.debug(f"已通过Redis更新任务[{eval_id}]状态: {status.value}")
#         except Exception as e:
#             logger.error(f"Redis更新任务状态失败: {str(e)}")

# def update_task_progress(db: Session, eval_id: int, progress: float):
#     """仅更新任务进度，不查询完整对象
    
#     Args:
#         db: 数据库会话
#         eval_id: 评估任务ID
#         progress: 进度百分比
#     """
#     try:
#         # 使用更高效的方式只更新progress字段
#         from sqlalchemy import text
        
#         # 先检查任务结果字段的当前值
#         stmt = text("SELECT results FROM evaluations WHERE id = :id")
#         result = db.execute(stmt, {"id": eval_id}).first()
        
#         if result and result[0]:
#             # 如果结果字段已存在，更新进度
#             current_results = result[0]
#             if isinstance(current_results, str):
#                 import json
#                 current_results = json.loads(current_results)
#             elif not isinstance(current_results, dict):
#                 current_results = {}
                
#             # 更新进度
#             current_results["progress"] = progress
            
#             # 更新到数据库
#             update_stmt = text("UPDATE evaluations SET results = :results WHERE id = :id")
#             db.execute(update_stmt, {"id": eval_id, "results": current_results})
#         else:
#             # 如果结果字段不存在，创建新的
#             update_stmt = text("UPDATE evaluations SET results = :results WHERE id = :id")
#             db.execute(update_stmt, {"id": eval_id, "results": {"progress": progress}})
            
#         # 提交事务
#         db.commit()
#     except Exception as e:
#         db.rollback()
#         logger.warning(f"更新任务进度出错: {str(e)}")
#         raise

# def batch_append_logs(eval_id: int, log_lines: list, redis_client=None):
#     """批量添加任务日志到Redis，避免重复
    
#     Args:
#         eval_id: 评估任务ID
#         log_lines: 新的日志行列表
#         redis_client: 可选的Redis客户端实例，如果提供将复用连接
        
#     Returns:
#         int: 成功添加的日志数量
#     """
#     if not log_lines:
#         return 0
    
#     # 过滤掉空行    
#     filtered_lines = [line.strip() for line in log_lines if line.strip()]
#     if not filtered_lines:
#         return 0
        
#     try:
#         # 使用RedisManager的批量添加方法
#         added_count = RedisManager.batch_append_logs(eval_id, filtered_lines)
#         if added_count > 0:
#             logger.debug(f"任务[{eval_id}]批量添加了{added_count}条日志")
#         return added_count
#     except Exception as e:
#         logger.error(f"批量添加日志出错: {str(e)}")
#         return 0

# def append_task_logs(eval_id: int, log_lines: list):
#     """增量添加任务日志到Redis，避免重复
    
#     Args:
#         eval_id: 评估任务ID
#         log_lines: 新的日志行列表
#     """
#     # 调用批量处理函数
#     batch_append_logs(eval_id, log_lines)

# def create_eval_config(eval_task):
#     """创建评估配置
    
#     Args:
#         eval_task: 评估任务对象
        
#     Returns:
#         dict: 评估配置
#     """
#     config = {
#         "model_name": eval_task.model_name,
#         "dataset_name": eval_task.dataset_name,
#         "model_params": eval_task.model_configuration,
#         "dataset_params": eval_task.dataset_configuration
#     }
    
#     # 添加额外配置
#     if hasattr(eval_task, "config_file") and eval_task.config_file:
#         config["config_file"] = eval_task.config_file
    
#     if hasattr(eval_task, "num_gpus") and eval_task.num_gpus:
#         config["num_gpus"] = eval_task.num_gpus
    
#     if hasattr(eval_task, "extra_args") and eval_task.extra_args:
#         config["extra_args"] = eval_task.extra_args
    
#     return config

# def update_task_metadata(db: Session, eval_id: int, metadata: dict):
#     """更新任务元数据
    
#     Args:
#         db: 数据库会话
#         eval_id: 评估任务ID
#         metadata: 元数据字典
#     """
#     eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
#     if eval_task:
#         # 如果结果字段是None，初始化为空字典
#         if eval_task.results is None:
#             eval_task.results = {}
        
#         # 将元数据添加到结果中
#         results = eval_task.results
        
#         # 如果没有metadata键，创建一个
#         if 'metadata' not in results:
#             results['metadata'] = {}
            
#         # 更新元数据
#         results['metadata'].update(metadata)
#         eval_task.results = results
#         db.commit()
#         logger.info(f"任务[{eval_id}]元数据已更新: {metadata}")

# def update_task_results(db: Session, eval_id: int, results):
#     """更新任务结果
    
#     Args:
#         db: 数据库会话
#         eval_id: 评估任务ID
#         results: 结果数据
#     """
#     eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
#     if eval_task:
#         eval_task.results = results
#         db.commit()
#         logger.info(f"任务[{eval_id}]结果已更新")

# def update_task_error(db: Session, eval_id: int, error_message: str):
#     """更新任务错误信息
    
#     Args:
#         db: 数据库会话
#         eval_id: 评估任务ID
#         error_message: 错误信息
#     """
#     eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
#     if eval_task:
#         # 如果结果字段是None，初始化为空字典
#         if eval_task.results is None:
#             eval_task.results = {}
        
#         # 将错误信息添加到结果中
#         results = eval_task.results
#         results["error"] = error_message
#         eval_task.results = results
#         db.commit()
#         logger.error(f"任务[{eval_id}]出错: {error_message}")
        
#         # 同时将错误信息添加到日志中
#         append_task_logs(eval_id, [f"错误: {error_message}"])

# def prepare_opencompass_config(model_configuration, dataset_configuration):
#     """准备OpenCompass配置
    
#     Args:
#         model_configuration: 模型配置
#         dataset_configuration: 数据集配置
        
#     Returns:
#         str: 配置文件路径
#     """
#     # 这里可以根据需要生成OpenCompass配置文件
#     # 简化起见，目前直接返回模型和数据集名称
#     return {
#         "model": model_configuration.get("model_name", ""),
#         "dataset": dataset_configuration.get("dataset_name", "")
#     } 


import os
import json
import time
import logging
import threading
import contextlib
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.orm import Session
from celery_app import celery_app
from core.database import SessionLocal
from models.eval import Evaluation, EvaluationStatus


from tasks.runners.runner import OpenCompassRunner, create_runner, get_runner, remove_runner
from utils.redis_manager import RedisManager
from tasks.task_evaluator import TaskEvaluator


# 配置日志
logger = logging.getLogger("eval_tasks")
logger.setLevel(logging.DEBUG)



@contextlib.contextmanager
def db_session():
    """数据库会话上下文管理器
    
    使用示例:
    with db_session() as db:
        # 使用数据库会话db
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def with_db_session(func):
    """数据库会话装饰器
    
    自动管理函数中的数据库会话资源
    """
    def wrapper(*args, **kwargs):
        with db_session() as session:
            # 将db会话作为第一个参数传入
            return func(session, *args, **kwargs)
    return wrapper

def handle_task_status_update(status_dict):
    """处理任务状态更新的回调函数
    
    当OpenCompassRunner状态变更时会调用此函数
    
    Args:
        status_dict: 包含状态信息的字典
    """
    # 获取任务ID，假设已在runner初始化时设置
    task_id = int(status_dict.get('task_id', -1))
    if task_id == -1:
        logger.warning(f"收到状态更新回调，但缺少task_id: {status_dict}")
        return
        
    # 提取状态信息并更新数据库
    try:
        with db_session() as db:
            # 如果状态含有progress，则更新进度
            if 'progress' in status_dict:
                update_task_progress(db, task_id, status_dict['progress'])
                
            # 如果状态中含有完成标志，则更新任务状态
            if status_dict.get('status') == 'finished':
                is_successful = status_dict.get('is_successful', False)
                if is_successful:
                    update_task_status(db, task_id, EvaluationStatus.COMPLETED)
                else:
                    error_msg = status_dict.get('error_message', '未知错误')
                    update_task_error(db, task_id, error_msg)
                    update_task_status(db, task_id, EvaluationStatus.FAILED)
    except Exception as e:
        logger.error(f"处理状态更新回调时出错: {str(e)}")

@celery_app.task(bind=True, name='eval_task.run_evaluation', queue='eval_tasks')
def run_evaluation(self, eval_id: int):
    """
    运行评估任务

    Args:
        eval_id: 评估任务ID
        
    Returns:
        dict: 任务状态信息
    """
    # 创建任务执行器并执行任务
    evaluator = TaskEvaluator(self, eval_id)
    return evaluator.execute()

def update_task_status(db: Session, eval_id: int, status: EvaluationStatus, results=None):
    """更新任务状态
    
    Args:
        db: 数据库会话
        eval_id: 评估任务ID
        status: 任务状态
        results: 可选的任务结果
    """
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        eval_task.status = status
        if results:
            eval_task.results = results
        db.commit()
        
        # 通过Redis更新任务状态
        try:
            RedisManager.update_task_status(eval_id, {
                "status": status.value,
                "updated_at": datetime.now().isoformat()
            })
            logger.debug(f"已通过Redis更新任务[{eval_id}]状态: {status.value}")
        except Exception as e:
            logger.error(f"Redis更新任务状态失败: {str(e)}")

def update_task_progress(db: Session, eval_id: int, progress: float):
    """仅更新任务进度，不查询完整对象
    
    Args:
        db: 数据库会话
        eval_id: 评估任务ID
        progress: 进度百分比
    """
    try:
        # 使用更高效的方式只更新progress字段
        from sqlalchemy import text
        
        # 先检查任务结果字段的当前值
        stmt = text("SELECT results FROM evaluations WHERE id = :id")
        result = db.execute(stmt, {"id": eval_id}).first()
        
        if result and result[0]:
            # 如果结果字段已存在，更新进度
            current_results = result[0]
            if isinstance(current_results, str):
                import json
                current_results = json.loads(current_results)
            elif not isinstance(current_results, dict):
                current_results = {}
                
            # 更新进度
            current_results["progress"] = progress
            
            # 更新到数据库
            update_stmt = text("UPDATE evaluations SET results = :results WHERE id = :id")
            db.execute(update_stmt, {"id": eval_id, "results": current_results})
        else:
            # 如果结果字段不存在，创建新的
            update_stmt = text("UPDATE evaluations SET results = :results WHERE id = :id")
            db.execute(update_stmt, {"id": eval_id, "results": {"progress": progress}})
            
        # 提交事务
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"更新任务进度出错: {str(e)}")
        raise

def batch_append_logs(eval_id: int, log_lines: list, redis_client=None):
    """批量添加任务日志到Redis，避免重复
    
    Args:
        eval_id: 评估任务ID
        log_lines: 新的日志行列表
        redis_client: 可选的Redis客户端实例，如果提供将复用连接
        
    Returns:
        int: 成功添加的日志数量
    """
    if not log_lines:
        return 0
    
    # 过滤掉空行    
    filtered_lines = [line.strip() for line in log_lines if line.strip()]
    if not filtered_lines:
        return 0
        
    try:
        # 使用RedisManager的批量添加方法
        added_count = RedisManager.batch_append_logs(eval_id, filtered_lines)
        if added_count > 0:
            logger.debug(f"任务[{eval_id}]批量添加了{added_count}条日志")
        return added_count
    except Exception as e:
        logger.error(f"批量添加日志出错: {str(e)}")
        return 0

def append_task_logs(eval_id: int, log_lines: list):
    """增量添加任务日志到Redis，避免重复
    
    Args:
        eval_id: 评估任务ID
        log_lines: 新的日志行列表
    """
    # 调用批量处理函数
    batch_append_logs(eval_id, log_lines)

def create_eval_config(eval_task):
    """创建评估配置
    
    Args:
        eval_task: 评估任务对象
        
    Returns:
        dict: 评估配置
    """
    config = {
        "model_name": eval_task.model_name,
        "dataset_name": eval_task.dataset_name,
        "model_params": eval_task.model_configuration,
        "dataset_params": eval_task.dataset_configuration
    }
    
    # 添加额外配置
    if hasattr(eval_task, "config_file") and eval_task.config_file:
        config["config_file"] = eval_task.config_file
    
    if hasattr(eval_task, "num_gpus") and eval_task.num_gpus:
        config["num_gpus"] = eval_task.num_gpus
    
    if hasattr(eval_task, "extra_args") and eval_task.extra_args:
        config["extra_args"] = eval_task.extra_args
    
    return config

def update_task_metadata(db: Session, eval_id: int, metadata: dict):
    """更新任务元数据
    
    Args:
        db: 数据库会话
        eval_id: 评估任务ID
        metadata: 元数据字典
    """
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        # 如果结果字段是None，初始化为空字典
        if eval_task.results is None:
            eval_task.results = {}
        
        # 将元数据添加到结果中
        results = eval_task.results
        
        # 如果没有metadata键，创建一个
        if 'metadata' not in results:
            results['metadata'] = {}
            
        # 更新元数据
        results['metadata'].update(metadata)
        eval_task.results = results
        db.commit()
        logger.info(f"任务[{eval_id}]元数据已更新: {metadata}")

def update_task_results(db: Session, eval_id: int, results):
    """更新任务结果
    
    Args:
        db: 数据库会话
        eval_id: 评估任务ID
        results: 结果数据
    """
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        eval_task.results = results
        db.commit()
        logger.info(f"任务[{eval_id}]结果已更新")

def update_task_error(db: Session, eval_id: int, error_message: str):
    """更新任务错误信息
    
    Args:
        db: 数据库会话
        eval_id: 评估任务ID
        error_message: 错误信息
    """
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        # 如果结果字段是None，初始化为空字典
        if eval_task.results is None:
            eval_task.results = {}
        
        # 将错误信息添加到结果中
        results = eval_task.results
        results["error"] = error_message
        eval_task.results = results
        db.commit()
        logger.error(f"任务[{eval_id}]出错: {error_message}")
        
        # 同时将错误信息添加到日志中
        append_task_logs(eval_id, [f"错误: {error_message}"])

def prepare_opencompass_config(model_configuration, dataset_configuration):
    """准备OpenCompass配置
    
    Args:
        model_configuration: 模型配置
        dataset_configuration: 数据集配置
        
    Returns:
        str: 配置文件路径
    """
    # 这里可以根据需要生成OpenCompass配置文件
    # 简化起见，目前直接返回模型和数据集名称
    return {
        "model": model_configuration.get("model_name", ""),
        "dataset": dataset_configuration.get("dataset_name", "")
    } 