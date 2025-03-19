from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """用户基础信息"""
    username: str
    email: EmailStr
    display_name: Optional[str] = None
    avatar: Optional[str] = None

class UserCreate(UserBase):
    """用户创建请求"""
    password: str  # 前端传入的字段仍为password
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra='allow'
    )

class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str  # 前端传入的字段仍为password
    
    model_config = ConfigDict(
        populate_by_name=True,
        extra='allow'
    )

class UserInDB(UserBase):
    """数据库中的用户"""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True
    )

class UserResponse(UserInDB):
    """返回给客户端的用户信息"""
    pass

class Token(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    """令牌数据"""
    username: Optional[str] = None 