import logging
from models.user import User
from sqlalchemy.orm import Session
from api.deps import get_db, get_current_user
from schemas.user import UserResponse
from utils.avatar_helper import AvatarHelper
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File


router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/avatar", response_model=UserResponse)
async def update_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户头像
    
    Args:
        file: 上传的头像文件
        current_user: 当前登录用户
        db: 数据库会话
        
    Returns:
        UserResponse: 更新后的用户信息
    """
    try:
        # 保存头像
        avatar_url = await AvatarHelper.save_avatar(file, current_user.id)
        
        # 更新用户记录
        current_user.avatar = avatar_url
        db.commit()
        db.refresh(current_user)
        
        # 返回更新后的用户信息
        from services.auth_service import auth_service
        return auth_service.user_to_response(current_user)
    except Exception as e:
        logger.error(f"更新头像失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新头像失败"
        ) 