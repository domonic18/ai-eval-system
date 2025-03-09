from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, text, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from core.database import Base, TimestampMixin


class ArenaStatus(PyEnum):
    """竞技场状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败

class Arena(Base, TimestampMixin):
    """竞技场模型"""
    __tablename__ = "arenas"

    id = Column(Integer, primary_key=True, index=True, comment="竞技场ID")
    name = Column(String(255), nullable=False, comment="竞技场名称")
    description = Column(Text, nullable=True, comment="竞技场描述")
    status = Column(
        Enum(ArenaStatus, name="arena_status", values_callable=lambda x: [e.value for e in x]),
        default=ArenaStatus.PENDING,
        nullable=False,
        index=True,
        comment="状态（pending/running/completed/failed）"
    )
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, comment="使用的数据集")
    configuration = Column(JSON, nullable=True, comment="竞技场配置")
    results = Column(JSON, nullable=True, comment="聚合结果（JSON 格式）")
    user_id = Column(Integer, ForeignKey("users.id"), index=True, comment="创建者ID")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), 
                      server_default=text("CURRENT_TIMESTAMP"),
                      onupdate=text("CURRENT_TIMESTAMP"),
                      comment="最后更新时间")
    
    # 关系
    user = relationship("User", back_populates="arenas")
    dataset = relationship("Dataset", back_populates="arenas")
    participants = relationship("ArenaParticipant", back_populates="arena", cascade="all, delete-orphan")

class ArenaParticipant(Base, TimestampMixin):
    """竞技场参与者模型"""
    __tablename__ = "arena_participants"
    id = Column(Integer, primary_key=True, index=True, comment="参与记录ID")
    arena_id = Column(Integer, ForeignKey("arenas.id"), index=True, comment="关联竞技场ID")
    model_id = Column(Integer, ForeignKey("ai_models.id"), index=True, comment="关联模型ID")
    score = Column(Float, nullable=True, index=True, comment="综合得分（根据配置计算）")
    rank = Column(Integer, nullable=True, index=True, comment="排名（运行时动态计算）")
    results = Column(JSON, nullable=True, comment="原始评估结果（JSON 格式）")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="参与时间")
    
    # 双向关系
    arena = relationship("Arena", back_populates="participants")
    model = relationship("AIModel", back_populates="participants")