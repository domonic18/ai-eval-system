from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean, text
from sqlalchemy.orm import relationship
from apps.server.src.db import Base

class AIModel(Base):
    """AI模型库"""
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="模型名称")
    provider = Column(String(100), nullable=False, comment="提供商")
    description = Column(Text, nullable=True, comment="模型描述")
    model_type = Column(String(50), nullable=False, comment="模型类型")
    version = Column(String(50), nullable=True, comment="版本")
    configuration = Column(JSON, nullable=True, comment="模型配置")
    is_public = Column(Boolean, default=True, comment="是否公开")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="创建者ID")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), 
                        onupdate=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间")
    
    # 关系
    user = relationship("User", backref="models") 