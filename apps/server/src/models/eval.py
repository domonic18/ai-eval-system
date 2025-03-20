from sqlalchemy import Column, Integer, String, JSON, DateTime, Enum, Text, Float, ForeignKey, text
from sqlalchemy.ext.hybrid import hybrid_property 
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from core.database import Base, TimestampMixin


class EvaluationStatus(PyEnum):
    """评估状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    STOPPED = "stopped"      # 已停止
    TERMINATED = "terminated"  # 已终止
    UNKNOWN = "unknown"      # 未知状态

class EvaluationType(PyEnum):
    """评估类型枚举"""
    TEXT = "text"
    MULTIMODAL = "multimodal"
    AGENT = "agent"


class Evaluation(Base, TimestampMixin):
    """评估模型"""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True, comment="任务名称")
    eval_type = Column(String(255), nullable=False, default=EvaluationType.TEXT.value, comment="评估类型(文字/多模态/Agent)")
    model_name = Column(String(255), nullable=False, comment="模型名称")
    dataset_names = Column(JSON, nullable=False, comment="数据集名称列表")
    model_configuration = Column(JSON, nullable=True, comment="模型配置")
    dataset_configuration = Column(JSON, nullable=True, comment="数据集配置")
    eval_config = Column(JSON, nullable=True, comment="评估配置")
    env_vars = Column(JSON, default={}, comment="环境变量（API_URL/API_KEY等）") 
    status = Column(String(50), nullable=False, index=True, default=EvaluationStatus.PENDING.value, comment="任务状态")
    task_id = Column(String(255), nullable=True, index=True, comment="Celery 任务 ID")
    error_message = Column(Text, nullable=True, comment="错误信息")
    log_dir = Column(String(255), nullable=True, comment="日志目录")
    progress = Column(Float, nullable=False, default=0.0, comment="进度百分比")
    results = Column(JSON, nullable=True, comment="评估结果")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="创建者用户ID")
    
    created_at = Column(DateTime(timezone=True),
                   server_default=text('CURRENT_TIMESTAMP(6)'),
                   comment="创建时间（北京时间）")
    updated_at = Column(DateTime(timezone=True),
                   server_default=text('CURRENT_TIMESTAMP(6)'),
                   onupdate=text('CURRENT_TIMESTAMP(6)'),
                   comment="更新时间（北京时间）")

    # 添加用户关系，实现联合查询
    user = relationship("User", backref="evaluations")

    @hybrid_property
    def formatted_results(self) -> dict:
        """格式化后的结果展示结构"""
        return {
            'scores': self._parse_scores(),
            'prediction_files': self._list_prediction_files()
        }
    
    def _parse_scores(self):
        """从summary解析得分"""
        if not self.results or 'summary' not in self.results:
            return {}
        return {item['dataset']: item['accuracy'] 
                for item in self.results.get('summary', [])}
    
    def _list_prediction_files(self):
        """列出预测文件"""
        if not self.results or 'prediction_files' not in self.results:
            return []
        return [f"predictions/{f}" 
                for f in self.results.get('prediction_files', [])]

    @hybrid_property
    def result_details(self) -> dict:
        return {
            "model_metrics": self.results.get('metrics', {}) if self.results else {},
            "prediction_paths": self.results.get('prediction_files', {}) if self.results else {}
        }