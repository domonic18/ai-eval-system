from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str

class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str = "Bearer"


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: EmailStr
    is_admin: bool
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True) 