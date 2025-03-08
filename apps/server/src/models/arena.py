from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Float, text
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from core.database import Base


class ArenaStatus(PyEnum):
    """竞技场状态枚举"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败

class Arena(Base):
    """竞技场模型"""
    __tablename__ = "arenas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="竞技场名称")
    description = Column(Text, nullable=True, comment="竞技场描述")
    status = Column(String(50), nullable=False, default=ArenaStatus.PENDING.value, comment="状态")
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, comment="使用的数据集")
    configuration = Column(JSON, nullable=True, comment="竞技场配置")
    results = Column(JSON, nullable=True, comment="竞技结果")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), 
                        onupdate=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间")
    
    # 关系
    user = relationship("User", backref="arenas")
    dataset = relationship("Dataset")

class ArenaParticipant(Base):
    """竞技场参与者模型"""
    __tablename__ = "arena_participants"

    id = Column(Integer, primary_key=True, index=True)
    arena_id = Column(Integer, ForeignKey("arenas.id"), nullable=False, comment="竞技场ID")
    model_id = Column(Integer, ForeignKey("ai_models.id"), nullable=False, comment="模型ID")
    score = Column(Float, nullable=True, comment="得分")
    rank = Column(Integer, nullable=True, comment="排名")
    results = Column(JSON, nullable=True, comment="详细结果")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    
    # 关系
    arena = relationship("Arena", backref="participants")
    model = relationship("AIModel") 