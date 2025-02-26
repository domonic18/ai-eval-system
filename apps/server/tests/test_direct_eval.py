#!/usr/bin/env python3
# 直接测试评估服务

import os
import sys
import json
import traceback
from pydantic import BaseModel
from typing import Dict, List, Any

# 添加项目根目录到Python路径
current_path = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
sys.path.insert(0, root_path)
print(f"已添加项目根目录到Python路径: {root_path}")

# 导入环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(root_path, "apps", "server", ".env"))

# 导入必要的模块
from apps.server.src.db import SessionLocal, db
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.schemas.eval import EvaluationCreate

# 定义测试数据
class TestData(BaseModel):
    task_name: str
    model_configuration: Dict[str, Any]
    dataset_config: Dict[str, Any]

def create_evaluation_task(eval_data):
    """直接创建评估任务（避开FastAPI依赖）
    
    Args:
        eval_data: 评估数据对象
    """
    # 创建数据库会话
    session = SessionLocal()
    
    try:
        # 创建评估任务记录
        db_eval = Evaluation(
            task_name=eval_data.task_name,
            model_configuration=eval_data.model_configuration,
            dataset_config=eval_data.dataset_config
        )
        
        # 这里使用session而不是db
        session.add(db_eval)
        session.commit()
        session.refresh(db_eval)
        
        print(f"✅ 成功创建评估任务，ID: {db_eval.id}")
        
        try:
            # 启动Celery任务
            from apps.server.src.tasks.eval_tasks import run_evaluation
            print(f"任务函数: {run_evaluation}")
            
            task = run_evaluation.delay(db_eval.id)
            print(f"任务已提交，任务ID: {task.id}")
            
            # 更新任务ID
            db_eval.celery_task_id = task.id
            session.commit()
            
            return {
                "id": db_eval.id,
                "task_name": db_eval.task_name,
                "status": db_eval.status.value,
                "celery_task_id": db_eval.celery_task_id
            }
            
        except Exception as e:
            print(f"Celery错误: {str(e)}")
            traceback.print_exc()
            
            db_eval.status = EvaluationStatus.FAILED
            db_eval.log_output = f"任务队列连接失败: {str(e)}"
            session.commit()
            
            return {
                "id": db_eval.id,
                "task_name": db_eval.task_name,
                "status": db_eval.status.value,
                "error": str(e)
            }
            
    except Exception as e:
        session.rollback()
        print(f"创建评估任务失败: {str(e)}")
        traceback.print_exc()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    # 测试数据
    test_data = TestData(
        task_name="测试直接调用评估服务",
        model_configuration={
            "model_name": "gpt-3.5-turbo",
            "parameters": {"temperature": 0.7, "top_p": 0.9}
        },
        dataset_config={
            "dataset_name": "mmlu",
            "split": "test",
            "subset": ["math", "computer_science"]
        }
    )
    
    # 调用创建评估任务函数
    try:
        result = create_evaluation_task(test_data)
        print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        traceback.print_exc() 