from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Any, Dict

from api.deps import get_db
from schemas.user import UserCreate, UserResponse, Token
from services.auth_service import auth_service
from models.user import User
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth2密码承载令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """获取访问令牌
    
    Args:
        form_data: 表单数据（用户名和密码）
        db: 数据库会话
        
    Returns:
        Dict[str, str]: 包含访问令牌和令牌类型的字典
    """
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
async def register_user(user_create: UserCreate, db: Session = Depends(get_db)):
    """注册新用户"""
    try:
        user = auth_service.register_user(db, user_create)
        return auth_service.user_to_response(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=Dict[str, Any])
async def login(
    user_data: dict,
    db: Session = Depends(get_db)
) -> Any:
    """用户登录
    
    Args:
        user_data: 包含用户名和密码的字典
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 包含访问令牌、令牌类型和用户信息的字典
    """
    user = auth_service.authenticate_user(db, user_data.get("username"), user_data.get("password"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "avatar": user.avatar,
            "is_admin": user.is_admin
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_user_info(current_user: User = Depends(auth_service.get_current_user)):
    """获取当前用户信息"""
    return auth_service.user_to_response(current_user) 