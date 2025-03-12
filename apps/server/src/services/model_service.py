from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from models.model import AIModel
from api.deps import get_db
from schemas.model import ModelOut, ModelCreate, ModelUpdate
import logging
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

class ModelService:
    """模型服务"""
    
    @staticmethod
    def get_models(db: Session, include_inactive: bool = False) -> List[ModelOut]:
        """获取模型列表"""
        try:
            query = db.query(AIModel)
            if not include_inactive:
                query = query.filter(AIModel.is_active == True)
            models = query.all()
            return [ModelOut.from_orm(model) for model in models]
        except Exception as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="无法获取模型列表"
            )

    @staticmethod
    def create_model(db: Session, model_data: ModelCreate, user_id: int) -> ModelOut:
        """创建新模型"""
        try:
            db_model = AIModel(
                **model_data.dict(),
                user_id=user_id,
                is_active=True
            )
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            return ModelOut.from_orm(db_model)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"模型名称冲突: {model_data.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="模型名称已存在"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"创建模型失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建模型失败"
            )

    @staticmethod
    def update_model(db: Session, model_id: int, model_data: ModelUpdate, user_id: int) -> ModelOut:
        """更新模型信息"""
        db_model = db.query(AIModel).filter(
            AIModel.id == model_id,
            AIModel.user_id == user_id
        ).first()

        if not db_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在或无权操作"
            )

        try:
            update_data = model_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_model, key, value)
            
            db.commit()
            db.refresh(db_model)
            return ModelOut.from_orm(db_model)
        except Exception as e:
            db.rollback()
            logger.error(f"更新模型失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新模型失败"
            )

    @staticmethod
    def delete_model(db: Session, model_id: int, user_id: int) -> dict:
        """删除模型（软删除）"""
        db_model = db.query(AIModel).filter(
            AIModel.id == model_id,
            AIModel.user_id == user_id
        ).first()

        if not db_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="模型不存在或无权操作"
            )

        try:
            # 检查是否有关联数据
            if db_model.participants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="存在关联评测任务，无法删除"
                )

            # 软删除
            db_model.is_active = False
            db.commit()
            return {"success": True, "message": "模型已删除"}
        except HTTPException as e:
            raise e
        except Exception as e:
            db.rollback()
            logger.error(f"删除模型失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除模型失败"
            )

# 创建服务实例
model_service = ModelService() 