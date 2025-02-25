import os
import sys
import json
import logging
from ..celery_app import celery_app
from datetime import datetime
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.eval import Evaluation, EvaluationStatus
from ..config import settings
from pathlib import Path

# 使用相对于项目根目录的绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
OPENCOMPASS_PATH = os.path.join(BASE_DIR, "libs", "OpenCompass")
print(f"OpenCompass路径: {OPENCOMPASS_PATH}")
sys.path.append(OPENCOMPASS_PATH)

logger = logging.getLogger("eval_tasks")

@celery_app.task(bind=True, name='eval_task.run_evaluation', queue='eval_tasks')
def run_evaluation(self, eval_id: int):
    """运行评测任务的Celery任务"""
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
        dataset_config = eval_task.dataset_config
        
        # 上报初始进度
        self.update_state(state='PROGRESS', meta={'progress': 0, 'status': '准备中...'})
        
        # 准备OpenCompass配置
        config_file = prepare_opencompass_config(model_config, dataset_config)
        
        # 模拟OpenCompass API调用
        try:
            # 实际项目中，这里调用OpenCompass，目前先模拟
            log_output = []

            # 模拟评测进度
            for step in range(1, 5):
                progress = step * 20
                status_msg = f"评测中... 阶段 {step}/5"
                log_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {status_msg}")
                
                # 更新进度和日志
                update_task_log(db, eval_id, "\n".join(log_output))
                self.update_state(state='PROGRESS', meta={'progress': progress, 'status': status_msg})
                
                # 模拟处理时间
                import time
                time.sleep(2)  # 开发时缩短等待时间
            
            # 模拟评测结果
            result_summary = {
                "model_name": model_config.get("model_name", "默认模型"),
                "dataset": dataset_config.get("dataset_name", "默认数据集"),
                "score": 0.85,
                "metrics": {
                    "accuracy": 0.87,
                    "f1": 0.83,
                    "precision": 0.89,
                    "recall": 0.81
                },
                "completed_at": datetime.now().isoformat()
            }
            
            # 更新最终状态
            log_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 评测完成")
            update_task_log(db, eval_id, "\n".join(log_output))
            update_task_status(db, eval_id, EvaluationStatus.COMPLETED, result_summary)
            
            return {
                "status": "success",
                "eval_id": eval_id,
                "results": result_summary
            }
            
        except Exception as e:
            logger.exception(f"评测失败: {str(e)}")
            # 更新为失败状态
            update_task_status(db, eval_id, EvaluationStatus.FAILED, {"error": str(e)})
            
            return {
                "status": "failed",
                "message": str(e)
            }
    finally:
        db.close()

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

def prepare_opencompass_config(model_config, dataset_config):
    """准备OpenCompass配置文件"""
    import tempfile
    
    # 简化配置格式，实际项目需要适配OpenCompass的配置格式
    config = {
        "models": [model_config],
        "datasets": [dataset_config]
    }
    
    # 写入临时配置文件
    temp_dir = tempfile.mkdtemp()
    config_path = os.path.join(temp_dir, 'config.json')
    
    with open(config_path, 'w') as f:
        json.dump(config, f)
    
    return config_path 