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
from apps.server.src.tasks.opencompass_runner import create_runner, get_runner, remove_runner

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
    """运行评测任务的Celery任务"""
    start_time = time.time()
    logger.info(f"============ 任务[{eval_id}] 开始执行 ============")
    logger.info(f"任务[{eval_id}] 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    db = SessionLocal()
    try:
        # 更新任务状态为运行中
        update_task_status(db, eval_id, EvaluationStatus.RUNNING)
        
        # 获取评测任务配置
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        if not eval_task:
            logger.error(f"任务ID {eval_id} 不存在")
            return {"status": "failed", "message": "任务不存在"}
        
        # 解析配置
        model_config = eval_task.model_configuration
        dataset_config = eval_task.dataset_configuration
        
        # 上报初始进度
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': '准备中...'})
        logger.info(f"任务[{eval_id}] 初始化状态更新：准备中...")
        
        # 创建日志目录
        logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, f"eval_{eval_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logger.info(f"任务[{eval_id}] 日志文件创建：{log_file}")
        
        # 直接使用评估任务中存储的模型和数据集名称
        model_name = eval_task.model_name
        dataset_name = eval_task.dataset_name
        logger.info(f"任务[{eval_id}] 使用模型：{model_name}，数据集：{dataset_name}")
        
        # 创建任务运行器
        task_id = f"eval_{eval_id}"
        runner = create_runner(task_id, working_dir=BASE_DIR, opencompass_path=OPENCOMPASS_PATH)
        
        # 构建命令
        command = runner.build_command(model_name, dataset_name)
        logger.info(f"任务[{eval_id}] OpenCompass命令：{command}")
        
        # 启动OpenCompass评测
        logger.info(f"任务[{eval_id}] 正在启动OpenCompass...")
        success = runner.run(command, log_file)
        if not success:
            logger.error(f"任务[{eval_id}] 启动OpenCompass评测失败")
            update_task_status(db, eval_id, EvaluationStatus.FAILED, {"error": "启动评测失败"})
            update_task_log(db, eval_id, "启动OpenCompass评测失败")
            return {"status": "failed", "message": "启动评测失败"}
        
        # 任务启动成功，开始监控状态
        logger.info(f"任务[{eval_id}] OpenCompass评测已成功启动")
        update_task_log(db, eval_id, f"OpenCompass评测已启动，日志文件: {log_file}")
        
        # 每5秒检查一次状态并更新
        status_update_count = 0
        prev_progress = 0  # 初始化进度变量，避免引用错误
        
        while runner.is_running:
            status = runner.get_status()
            status_update_count += 1
            
            # 更新状态信息
            self.update_state(state='PROGRESS', meta={
                'progress': status['progress'],
                'status': status['status_message']
            })
            
            # 只在每5次更新（25秒）或进度变化时记录日志，避免日志过多
            if status_update_count % 5 == 0 or prev_progress != status['progress']:
                logger.info(f"任务[{eval_id}] 状态更新 #{status_update_count}: 进度={status['progress']}%, 状态={status['status_message']}")
            prev_progress = status['progress']
            
            # 更新日志
            recent_logs = "\n".join(status['recent_logs'][-10:])  # 最近10条日志
            update_task_log(db, eval_id, recent_logs)
            
            # 等待5秒
            time.sleep(5)
        
        # 任务结束后的处理
        final_status = runner.get_status()
        logger.info(f"任务[{eval_id}] OpenCompass评测已结束，返回码：{final_status['return_code']}")
        
        # 如果任务成功完成
        if final_status['return_code'] == 0:
            # 解析结果
            results = {"message": "评测完成", "logs": final_status['recent_logs']}
            logger.info(f"任务[{eval_id}] 评测成功完成")
            update_task_status(db, eval_id, EvaluationStatus.COMPLETED, results)
            update_task_log(db, eval_id, "OpenCompass评测已完成")
            return {"status": "success", "message": "评测完成"}
        else:
            # 任务失败
            error_info = {"error": f"评测失败，返回码: {final_status['return_code']}", "logs": final_status['recent_logs']}
            logger.error(f"任务[{eval_id}] 评测失败，返回码：{final_status['return_code']}")
            update_task_status(db, eval_id, EvaluationStatus.FAILED, error_info)
            update_task_log(db, eval_id, f"OpenCompass评测失败，返回码: {final_status['return_code']}")
            return {"status": "failed", "message": f"评测失败，返回码: {final_status['return_code']}"}
            
    except Exception as e:
        logger.exception(f"评测任务执行异常: {str(e)}")
        update_task_status(db, eval_id, EvaluationStatus.FAILED, {"error": str(e)})
        update_task_log(db, eval_id, f"评测任务执行异常: {str(e)}")
        return {"status": "failed", "message": str(e)}
    finally:
        # 释放资源
        remove_runner(f"eval_{eval_id}")
        db.close()
        
        # 记录任务结束信息
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"任务[{eval_id}] 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"任务[{eval_id}] 总耗时: {elapsed_time:.2f} 秒")
        logger.info(f"============ 任务[{eval_id}] 执行完毕 ============")

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