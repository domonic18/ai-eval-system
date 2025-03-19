import os
import secrets
import shutil
from fastapi import UploadFile, HTTPException
from typing import Optional
from core.config import settings
from pathlib import Path

# 确保上传目录存在
os.makedirs(settings.avatar_storage_dir, exist_ok=True)

class AvatarHelper:
    @staticmethod
    def get_default_avatar_url() -> str:
        """获取默认头像URL (由前端提供)"""
        return settings.default_avatar_url
    
    @staticmethod
    def format_avatar_url(avatar_path: Optional[str]) -> str:
        """格式化头像URL
        
        Args:
            avatar_path: 存储的头像路径
            
        Returns:
            str: 格式化后的头像URL
        """
        if not avatar_path:
            return settings.default_avatar_url
            
        # 如果已经是完整URL，则直接返回
        if avatar_path.startswith(("http://", "https://")):
            return avatar_path
            
        # 如果是相对路径并且已经包含前缀，直接返回
        if avatar_path.startswith(settings.avatar_url_prefix):
            return avatar_path
            
        # 如果是存储的相对路径，转换为API URL
        if "/" in avatar_path:
            # 只取文件名部分
            avatar_path = os.path.basename(avatar_path)
            
        return f"{settings.avatar_url_prefix}/{avatar_path}"
    
    @staticmethod
    async def save_avatar(file: UploadFile, user_id: int) -> str:
        """保存用户上传的头像
        
        Args:
            file: 上传的文件
            user_id: 用户ID
            
        Returns:
            str: 保存后的头像URL
        """
        # 验证文件类型
        if not file.content_type.startswith("image/") or file.content_type not in settings.allowed_avatar_types:
            raise HTTPException(status_code=400, detail="不支持的图片格式")
            
        # 检查文件大小
        try:
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()  # 获取文件大小
            file.file.seek(0)  # 重置文件指针
            
            if file_size > settings.max_avatar_size:
                raise HTTPException(status_code=400, detail=f"图片大小不能超过{settings.max_avatar_size // (1024*1024)}MB")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"无法验证文件大小: {str(e)}")
            
        # 生成唯一文件名
        file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".png"
        random_name = f"{user_id}_{secrets.token_hex(8)}{file_ext}"
        file_path = os.path.join(settings.avatar_storage_dir, random_name)
        
        # 保存文件
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")
        finally:
            await file.close()
            
        # 返回相对URL (不包含域名)
        return f"{settings.avatar_url_prefix}/{random_name}" 