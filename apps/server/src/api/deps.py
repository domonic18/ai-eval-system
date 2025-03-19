from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi.security import OAuth2PasswordBearer

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
def get_current_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")),
    db: Session = Depends(get_db)
) -> User:
    """完整的JWT认证实现"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. 解码JWT令牌
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False}
        )
        
        # 2. 验证令牌结构
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        # 3. 查询数据库获取用户
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
            
        # 4. 验证用户状态
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户已被禁用"
            )
            
        return user
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
