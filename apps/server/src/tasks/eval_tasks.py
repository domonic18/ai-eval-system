import os
import sys
import json
import logging
import time
from apps.server.src.celery_app import celery_app
from datetime import datetime
from sqlalchemy.orm import Session
from apps.server.src.db import SessionLocal
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.core.config import OPENCOMPASS_PATH
from pathlib import Path
from apps.server.src.tasks.opencompass_runner import OpenCompassRunner, create_runner, get_runner, remove_runner
from apps.server.src.utils.redis_manager import RedisManager  # 确保导入RedisManager

# 使用相对于项目根目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
print(f"OpenCompass路径: {OPENCOMPASS_PATH}")
sys.path.append(OPENCOMPASS_PATH)

# 配置日志
logger = logging.getLogger("eval_tasks")
logger.setLevel(logging.DEBUG)

# 确保日志目录存在
log_dir = os.path.join(BASE_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)

# 添加文件处理器
file_handler = logging.FileHandler(os.path.join(log_dir, "eval_tasks.log"))
file_handler.setLevel(logging.DEBUG)

# 添加控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 设置格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 添加处理器到日志记录器
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

@celery_app.task(bind=True, name='eval_task.run_evaluation', queue='eval_tasks')
def run_evaluation(self, eval_id: int):
    """
    运行评估任务

    Args:
        eval_id: 评估任务ID
    """
    logger.info(f"开始执行评估任务[{eval_id}]")
    
    # 获取数据库会话
    db = SessionLocal()
    
    # 更新任务状态为运行中
    update_task_status(db, eval_id, EvaluationStatus.RUNNING)
    
    try:
        # 读取评估任务
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not eval_task:
            raise ValueError(f"找不到评估任务: {eval_id}")
            
        # 创建配置
        eval_config = create_eval_config(eval_task)
        
        # 创建运行器
        from apps.server.src.core.config import OPENCOMPASS_PATH
        
        # 创建OpenCompass任务标识符
        task_id = f"eval_{eval_id}"
        
        # 清空之前的日志记录
        RedisManager.clear_logs(eval_id)
        
        # 使用辅助函数创建运行器
        runner = create_runner(
            task_id=task_id, 
            working_dir=str(BASE_DIR),
            opencompass_path=OPENCOMPASS_PATH
        )
        
        # 构建命令
        model_name = eval_task.model_name
        dataset_name = eval_task.dataset_name
        command = runner.build_command(model_name, dataset_name)
        
        # 创建日志文件
        logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"eval_{eval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # 启动运行器
        success = runner.run(command, log_file)
        
        if not success:
            raise ValueError(f"启动评估任务失败，无法执行命令: {command}")
        
        # 设置初始任务状态
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': '任务已启动'})
        
        # 设置任务元数据
        update_task_metadata(db, eval_id, {
            'pid': runner.process.pid if runner.process else None,
            'log_file': log_file
        })
        
        # 关闭初始的数据库连接，避免长时间占用
        db.close()
        
        # 启动独立的监控线程，而不是阻塞Celery任务
        import threading
        
        def monitor_task():
            """监控评估任务的独立线程"""
            status_update_count = 0
            prev_progress = 0
            # 用于追踪已处理的日志，避免重复添加
            processed_logs = set()
            # 存储Redis连接，以便在最后关闭
            redis_client = None
            # 记录最后一次重新创建db连接的时间
            last_db_refresh_time = time.time()
            
            try:
                # 获取Redis连接
                redis_client = RedisManager.get_instance()
                
                while runner.is_running:
                    # 获取独立的数据库会话，避免长时间持有连接
                    # 每30分钟刷新一次连接，避免连接超时问题
                    current_time = time.time()
                    renew_db_connection = (current_time - last_db_refresh_time) > 1800  # 30分钟
                    
                    db_session = None
                    try:
                        if renew_db_connection or status_update_count % 60 == 0:  # 每60次循环或30分钟刷新
                            db_session = SessionLocal()
                            last_db_refresh_time = current_time
                            logger.debug(f"任务[{eval_id}]刷新数据库连接")
                        
                        status = runner.get_status()
                        status_update_count += 1
                        
                        # 更新数据库中的任务状态 - 仅在有db_session时进行
                        if db_session and (status_update_count % 5 == 0 or prev_progress != status['progress']):
                            logger.info(f"任务[{eval_id}] 状态更新 #{status_update_count}: 进度={status['progress']}%, 状态={status['status_message']}")
                            try:
                                # 只更新任务状态，不获取完整的任务对象
                                update_task_progress(db_session, eval_id, status['progress'])
                            except Exception as db_error:
                                logger.warning(f"更新任务状态时出错: {str(db_error)}")
                        
                        prev_progress = status['progress']
                        
                        # 使用批量处理减少Redis操作频率
                        if 'recent_logs' in status and status['recent_logs']:
                            new_logs = []
                            for log_line in status['recent_logs']:
                                # 检查是否已处理过该日志
                                log_hash = hash(log_line.strip())
                                if log_hash not in processed_logs:
                                    processed_logs.add(log_hash)
                                    new_logs.append(log_line)
                            
                            # 只添加新的、未处理过的日志，批量处理
                            if new_logs:
                                # 一次性添加所有日志行，减少I/O操作
                                batch_append_logs(eval_id, new_logs, redis_client)
                    except Exception as loop_error:
                        logger.warning(f"监控循环中出错: {str(loop_error)}")
                    finally:
                        # 确保每次循环结束后关闭数据库连接
                        if db_session:
                            db_session.close()
                    
                    # 使用自适应等待间隔
                    wait_time = 5  # 默认5秒
                    # 如果进度变化缓慢，逐渐增加等待时间，最多10秒
                    if status_update_count > 10 and status_update_count % 10 == 0:
                        wait_time = min(10, 5 + status_update_count // 20)
                    
                    time.sleep(wait_time)
                
                # 任务结束后的处理
                is_finished = runner.is_finished
                is_successful = runner.is_successful
                
                # 获取新的数据库会话
                db_session = SessionLocal()
                try:
                    if is_finished:
                        if is_successful:
                            # 更新结果
                            results = runner.get_results()
                            update_task_results(db_session, eval_id, results)
                            update_task_status(db_session, eval_id, EvaluationStatus.COMPLETED)
                            logger.info(f"评估任务[{eval_id}]已完成")
                        else:
                            error_msg = runner.get_error_message()
                            update_task_error(db_session, eval_id, error_msg)
                            update_task_status(db_session, eval_id, EvaluationStatus.FAILED)
                            logger.error(f"评估任务[{eval_id}]失败: {error_msg}")
                finally:
                    # 关闭数据库会话
                    db_session.close()
                
                # 清理资源
                remove_runner(task_id)
            except Exception as e:
                logger.exception(f"监控任务[{eval_id}]时发生错误: {str(e)}")
                
                # 获取新的数据库会话来记录错误
                try:
                    db_session = SessionLocal()
                    update_task_error(db_session, eval_id, str(e))
                    update_task_status(db_session, eval_id, EvaluationStatus.FAILED)
                    db_session.close()
                except Exception as db_error:
                    logger.error(f"记录错误时数据库操作失败: {str(db_error)}")
                
                # 发生异常时也清理资源
                remove_runner(task_id)
            finally:
                # 清理资源
                # 确保在线程结束时不会留下未关闭的连接
                processed_logs.clear()
        
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_task, daemon=True)
        monitor_thread.start()
        
        # Celery任务立即返回，不再等待评估完成
        return {
            "message": f"评估任务[{eval_id}]已启动，正在后台执行",
            "eval_id": eval_id,
            "status": "RUNNING"
        }
        
    except Exception as e:
        logger.exception(f"启动评估任务[{eval_id}]时发生错误: {str(e)}")
        error_message = str(e)
        update_task_error(db, eval_id, error_message)
        update_task_status(db, eval_id, EvaluationStatus.FAILED)
        
        # 清理资源
        task_id = f"eval_{eval_id}"
        if get_runner(task_id):
            remove_runner(task_id)
        
        # 确保在返回前关闭数据库连接
        db.close()
            
        raise

def update_task_status(db: Session, eval_id: int, status: EvaluationStatus, results=None):
    """更新任务状态"""
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        eval_task.status = status
        if results:
            eval_task.results = results
        db.commit()

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

def update_task_log(db: Session, eval_id: int, log_text: str):
    """更新任务日志 - 已弃用，请使用append_task_logs函数"""
    logger.warning("update_task_log函数已弃用，请使用append_task_logs函数")
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        eval_task.log_output = log_text
        db.commit()

def batch_append_logs(eval_id: int, log_lines: list, redis_client=None):
    """批量添加任务日志到Redis，避免重复
    
    Args:
        eval_id: 评估任务ID
        log_lines: 新的日志行列表
        redis_client: 可选的Redis客户端实例，如果提供将复用连接
    """
    if not log_lines:
        return
    
    # 过滤掉空行    
    filtered_lines = [line.strip() for line in log_lines if line.strip()]
    if not filtered_lines:
        return
        
    try:
        # 使用已有连接或创建新连接
        client = redis_client or RedisManager.get_instance()
        log_key = RedisManager.get_log_key(eval_id)
        
        # 获取最近的日志用于去重
        recent_logs = client.lrange(log_key, -10, -1)
        
        # 过滤掉重复的日志行
        unique_lines = []
        for line in filtered_lines:
            if line not in recent_logs:
                unique_lines.append(line)
        
        # 如果没有新日志，直接返回
        if not unique_lines:
            return
            
        # 使用管道批量操作
        pipe = client.pipeline()
        
        # 批量添加日志
        for line in unique_lines:
            pipe.rpush(log_key, line)
            pipe.publish(RedisManager.get_log_channel(eval_id), line)
        
        # 设置过期时间
        pipe.expire(log_key, 86400)  # 1天
        
        # 执行管道操作
        pipe.execute()
        
        logger.debug(f"任务[{eval_id}]批量添加了{len(unique_lines)}条日志")
    except Exception as e:
        logger.error(f"批量添加日志出错: {str(e)}")

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