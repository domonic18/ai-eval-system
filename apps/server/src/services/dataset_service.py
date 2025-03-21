import logging
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.dataset import Dataset
from schemas.dataset import DatasetOut, DatasetCreate, DatasetUpdate


logger = logging.getLogger(__name__)

class DatasetService:
    """数据集服务"""
    
    @staticmethod
    def get_datasets(db: Session, include_inactive: bool = False) -> List[DatasetOut]:
        """获取数据集列表"""
        try:
            query = db.query(Dataset)
            if not include_inactive:
                query = query.filter(Dataset.is_active == True)
            datasets = query.all()
            return [DatasetOut.from_orm(dataset) for dataset in datasets]
        except Exception as e:
            logger.error(f"获取数据集列表失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="无法获取数据集列表"
            )

    @staticmethod
    def create_dataset(db: Session, dataset_data: DatasetCreate, user_id: int) -> DatasetOut:
        """创建新数据集"""
        try:
            db_dataset = Dataset(
                **dataset_data.dict(),
                user_id=user_id,
                is_active=True
            )
            db.add(db_dataset)
            db.commit()
            db.refresh(db_dataset)
            return DatasetOut.from_orm(db_dataset)
        except IntegrityError as e:
            db.rollback()
            logger.warning(f"数据集名称冲突: {dataset_data.name}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="数据集名称已存在"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"创建数据集失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建数据集失败"
            )

    @staticmethod
    def update_dataset(db: Session, dataset_id: int, dataset_data: DatasetUpdate, user_id: int) -> DatasetOut:
        """更新数据集信息"""
        db_dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.user_id == user_id
        ).first()

        if not db_dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据集不存在或无权操作"
            )

        try:
            update_data = dataset_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_dataset, key, value)
            
            db.commit()
            db.refresh(db_dataset)
            return DatasetOut.from_orm(db_dataset)
        except Exception as e:
            db.rollback()
            logger.error(f"更新数据集失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新数据集失败"
            )

    @staticmethod
    def delete_dataset(db: Session, dataset_id: int, user_id: int) -> dict:
        """删除数据集（软删除）"""
        db_dataset = db.query(Dataset).filter(
            Dataset.id == dataset_id,
            Dataset.user_id == user_id
        ).first()

        if not db_dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="数据集不存在或无权操作"
            )

        try:
            # 检查是否有关联数据
            if db_dataset.arenas:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="存在关联评测任务，无法删除"
                )

            # 软删除
            db_dataset.is_active = False
            db.commit()
            return {"success": True, "message": "数据集已删除"}
        except HTTPException as e:
            raise e
        except Exception as e:
            db.rollback()
            logger.error(f"删除数据集失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除数据集失败"
            )

# 创建服务实例
dataset_service = DatasetService() 