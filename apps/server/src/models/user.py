from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from core.database import Base, TimestampMixin
from sqlalchemy.orm import relationship


class User(Base, TimestampMixin):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码（加密存储）")
    email = Column(String(255), unique=True, nullable=False, index=True, comment="邮箱")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), 
                        onupdate=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间") 
    
    datasets = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    models = relationship("AIModel", back_populates="user", cascade="all, delete-orphan")
    arenas = relationship("Arena", back_populates="user", cascade="all, delete-orphan")