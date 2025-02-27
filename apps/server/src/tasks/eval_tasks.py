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
        
        # 启动独立的监控线程，而不是阻塞Celery任务
        import threading
        
        def monitor_task():
            """监控评估任务的独立线程"""
            status_update_count = 0
            prev_progress = 0
            
            try:
                while runner.is_running:
                    status = runner.get_status()
                    status_update_count += 1
                    
                    # 更新数据库中的任务状态
                    if status_update_count % 5 == 0 or prev_progress != status['progress']:
                        logger.info(f"任务[{eval_id}] 状态更新 #{status_update_count}: 进度={status['progress']}%, 状态={status['status_message']}")
                    prev_progress = status['progress']
                    
                    # 更新日志
                    recent_logs = "\n".join(status['recent_logs'][-10:])
                    update_task_log(db, eval_id, recent_logs)
                    
                    # 等待5秒
                    time.sleep(5)
                
                # 任务结束后的处理
                is_finished = runner.is_finished
                is_successful = runner.is_successful
                
                if is_finished:
                    if is_successful:
                        # 更新结果
                        results = runner.get_results()
                        update_task_results(db, eval_id, results)
                        update_task_status(db, eval_id, EvaluationStatus.COMPLETED)
                        logger.info(f"评估任务[{eval_id}]已完成")
                    else:
                        error_msg = runner.get_error_message()
                        update_task_error(db, eval_id, error_msg)
                        update_task_status(db, eval_id, EvaluationStatus.FAILED)
                        logger.error(f"评估任务[{eval_id}]失败: {error_msg}")
                    
                    # 清理资源
                    remove_runner(task_id)
            except Exception as e:
                logger.exception(f"监控任务[{eval_id}]时发生错误: {str(e)}")
                update_task_error(db, eval_id, str(e))
                update_task_status(db, eval_id, EvaluationStatus.FAILED)
                
                # 发生异常时也清理资源
                remove_runner(task_id)
        
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
            
        raise

def update_task_status(db: Session, eval_id: int, status: EvaluationStatus, results=None):
    """更新任务状态"""
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        eval_task.status = status
        if results:
            eval_task.results = results
        db.commit()

def update_task_log(db: Session, eval_id: int, log_text: str):
    """更新任务日志"""
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if eval_task:
        eval_task.log_output = log_text
        db.commit()

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