from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from apps.server.src.db import get_db
from apps.server.src.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from apps.server.src.services.auth_service import auth_service
import logging

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# OAuth2密码流程
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """注册新用户
    
    Args:
        user_data: 用户数据
        db: 数据库会话
        
    Returns:
        UserResponse: 用户信息
    """
    try:
        user = auth_service.register_user(db, user_data)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar=user.avatar,
            is_admin=user.is_admin
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"注册用户失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册用户失败: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,  # 使用自定义的UserLogin schema
    db: Session = Depends(get_db)
):
    """用户登录
    
    Args:
        login_data: 登录数据
        db: 数据库会话
        
    Returns:
        Token: 令牌信息
    """
    try:
        user = auth_service.authenticate_user(db, login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码不正确",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return auth_service.create_token_response(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户信息
    
    Args:
        token: 访问令牌
        db: 数据库会话
        
    Returns:
        UserResponse: 用户信息
    """
    user = auth_service.get_current_user(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        avatar=user.avatar,
        is_admin=user.is_admin
    ) 