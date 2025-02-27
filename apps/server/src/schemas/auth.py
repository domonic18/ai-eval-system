from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str

class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    is_admin: bool

class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: EmailStr
    avatar: Optional[str] = None
    is_admin: bool

    class Config:
        from_attributes = True 