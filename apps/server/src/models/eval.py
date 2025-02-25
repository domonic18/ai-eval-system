from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum as PyEnum

Base = declarative_base()

class EvaluationStatus(str, PyEnum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

class Evaluation(Base):
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(100), nullable=False)
    model_configuration = Column(JSON, nullable=False)
    dataset_config = Column(JSON, nullable=False)
    status = Column(Enum(EvaluationStatus), default=EvaluationStatus.PENDING)
    results = Column(JSON, nullable=True)  # 存储评测结果
    celery_task_id = Column(String(50), nullable=True)  # 存储Celery任务ID
    log_output = Column(Text, nullable=True)  # 存储任务日志
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow) 