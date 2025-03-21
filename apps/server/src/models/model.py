from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, Boolean, text
from sqlalchemy.orm import relationship
from core.database import Base, TimestampMixin


class AIModel(Base, TimestampMixin):
    """AI模型库"""
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True, comment="模型ID")
    name = Column(String(255), nullable=False, index=True, comment="模型名称（唯一标识）")
    provider = Column(String(100), nullable=False, comment="提供商")
    description = Column(Text, nullable=True, comment="模型描述（支持 Markdown）")
    model_type = Column(String(50), nullable=False, comment="模型类型")
    version = Column(String(50), nullable=True, comment="版本")
    configuration = Column(JSON, nullable=True, comment="运行时配置（API密钥/超参等敏感信息应加密）")
    is_public = Column(Boolean, default=True, index=True, comment="可见性（True=公开，False=私有）")
    is_active = Column(Boolean, default=True, comment="是否激活(软删除控制)")
    user_id = Column(Integer, ForeignKey("users.id"), index=True, comment="所属用户ID")

    created_at = Column(DateTime(timezone=True),
                        server_default=text('CURRENT_TIMESTAMP(6)'),
                        comment="创建时间（北京时间）")
    updated_at = Column(DateTime(timezone=True),
                        server_default=text('CURRENT_TIMESTAMP(6)'),
                        onupdate=text('CURRENT_TIMESTAMP(6)'),
                        comment="更新时间（北京时间）")
    
    # 关系
    user = relationship("User", back_populates="models")
    participants = relationship("ArenaParticipant", back_populates="model", cascade="all, delete-orphan")