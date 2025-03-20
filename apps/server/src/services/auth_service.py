from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from models.user import User
from schemas.auth import UserCreate, Token
from api.deps import get_db
import os
import logging
from utils.password import verify_password, get_password_hash
from schemas.user import UserInDB, UserResponse
from core.config import settings
from utils.avatar_helper import AvatarHelper

# 配置日志
logger = logging.getLogger(__name__)

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2密码流程
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码

        Args:
            plain_password: 明文密码
            hashed_password: 已哈希密码

        Returns:
            bool: 密码是否匹配
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码哈希

        Args:
            password: 明文密码

        Returns:
            str: 密码哈希
        """
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """注册新用户

        Args:
            db: 数据库会话
            user_data: 用户数据

        Returns:
            User: 已创建的用户
        """
        # 检查用户名是否已存在
        if db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"用户名 '{user_data.username}' 已被使用"
            )

        # 检查邮箱是否已存在
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"邮箱 '{user_data.email}' 已被注册"
            )

        # 创建新用户
        hashed_password = AuthService.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            display_name=user_data.display_name or user_data.username,
            avatar=user_data.avatar or settings.default_avatar_url,
            is_active=True,
            is_admin=False
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """认证用户

        Args:
            db: 数据库会话
            username: 用户名
            password: 密码

        Returns:
            Optional[User]: 认证成功的用户，认证失败返回None
        """
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            raise ValueError("用户已被停用")
        return user

    @staticmethod
    def _extract_user_from_token(db: Session, token: str) -> Optional[User]:
        """从令牌中提取用户信息（内部方法）

        Args:
            db: 数据库会话
            token: JWT令牌

        Returns:
            Optional[User]: 当前用户，解析失败返回None
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            username = payload.get("sub")
            if username is None:
                return None
        except JWTError:
            return None

        user = db.query(User).filter(User.username == username).first()
        return user

    def get_current_user(self, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        """获取当前用户（可用作FastAPI依赖项）

        Args:
            token: JWT令牌
            db: 数据库会话

        Returns:
            User: 当前用户，如果无效则抛出异常
        """
        user = self._extract_user_from_token(db, token)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="无效的凭证或凭证已过期",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user

    @staticmethod
    def user_to_response(user: User) -> UserResponse:
        """将用户模型转换为响应模型
        
        Args:
            user: 用户模型
            
        Returns:
            UserResponse: 用户响应模型
        """
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            avatar=user.avatar,
            is_admin=user.is_admin,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

# 创建服务实例
auth_service = AuthService() 