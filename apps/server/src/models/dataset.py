from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, text, Boolean
from sqlalchemy.orm import relationship
from core.database import Base, TimestampMixin


class Dataset(Base, TimestampMixin):
    """数据集模型"""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="数据集名称")
    description = Column(Text, nullable=True, comment="数据集描述")
    type = Column(String(50), nullable=False, comment="数据集类型")
    category = Column(String(50), nullable=True, comment="数据集分类")
    file_path = Column(String(255), nullable=True, comment="数据集文件路径")
    configuration = Column(JSON, nullable=True, comment="数据集配置")
    is_active = Column(Boolean, default=True, comment="是否激活(软删除控制)")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    created_at = Column(DateTime(timezone=True), 
                        server_default=text('CURRENT_TIMESTAMP(6)'),
                        comment="创建时间（北京时间）")
    updated_at = Column(DateTime(timezone=True), 
                        server_default=text('CURRENT_TIMESTAMP(6)'),
                        onupdate=text('CURRENT_TIMESTAMP(6)'),
                        comment="更新时间（北京时间）")
    
    # 关系
    user = relationship("User", back_populates="datasets")
    arenas = relationship("Arena", back_populates="dataset")