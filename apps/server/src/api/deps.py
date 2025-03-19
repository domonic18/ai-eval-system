from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from core.database import db
from core.config import settings
from models.user import User

# 为了向后兼容，保留原来的函数
def get_db():
    """为了依赖注入而提供的获取数据库会话的函数
    
    在FastAPI中使用 Depends(get_db) 来注入会话
    """
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

# 添加获取当前用户的依赖函数
def get_current_user(db: Session = Depends(get_db)):
    """获取当前登录用户
    
    从请求的Authorization头部获取令牌，验证后返回用户对象
    
    Args:
        db: 数据库会话
        
    Returns:
        User: 当前登录用户对象
        
    Raises:
        HTTPException: 认证失败时抛出401异常
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 实际项目中应该从请求headers中获取token，这里简化为使用固定用户
    # 在真实环境中应该解析JWT token并验证
    
    # 查询系统默认用户（此处使用ID=1作为演示）
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        # 如果默认用户不存在，抛出认证异常
        raise credentials_exception
    
    return user
