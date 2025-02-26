from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum, Text, Float
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from apps.server.src.db import Base

class EvaluationStatus(PyEnum):
    """评估状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    STOPPED = "stopped"      # 已停止
    UNKNOWN = "unknown"      # 未知状态

class Evaluation(Base):
    """评估模型"""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(255), nullable=False, comment="模型名称")
    dataset_name = Column(String(255), nullable=False, comment="数据集名称")
    model_configuration = Column(JSON, nullable=True, comment="模型配置")
    dataset_configuration = Column(JSON, nullable=True, comment="数据集配置")
    eval_config = Column(JSON, nullable=True, comment="评估配置")
    status = Column(String(50), nullable=False, default=EvaluationStatus.PENDING.value, comment="任务状态")
    task_id = Column(String(255), nullable=True, comment="Celery 任务 ID")
    error_message = Column(Text, nullable=True, comment="错误信息")
    log_dir = Column(String(255), nullable=True, comment="日志目录")
    progress = Column(Float, nullable=False, default=0.0, comment="进度百分比")
    results = Column(JSON, nullable=True, comment="评估结果")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间") 