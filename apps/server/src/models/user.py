from sqlalchemy import Column, Integer, String, DateTime, Boolean, text
from apps.server.src.db import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码（加密存储）")
    email = Column(String(255), unique=True, nullable=False, comment="邮箱")
    avatar = Column(String(255), nullable=True, comment="头像URL")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    created_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), 
                        onupdate=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间") 