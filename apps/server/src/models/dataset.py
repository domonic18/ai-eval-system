from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey, text
from sqlalchemy.orm import relationship
from core.database import Base, TimestampMixin


class Dataset(Base, TimestampMixin):
    """数据集模型"""
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="数据集名称")
    description = Column(Text, nullable=True, comment="数据集描述")
    type = Column(String(50), nullable=False, comment="数据集类型")
    file_path = Column(String(255), nullable=True, comment="数据集文件路径")
    configuration = Column(JSON, nullable=True, comment="数据集配置")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), 
                        onupdate=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="datasets")