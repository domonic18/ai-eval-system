from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class DatasetBase(BaseModel):
    """数据集基类"""
    name: str
    type: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    configuration: Optional[dict] = None

class DatasetCreate(DatasetBase):
    pass

class DatasetUpdate(BaseModel):
    """数据集更新结构"""
    description: Optional[str] = None
    file_path: Optional[str] = None
    configuration: Optional[dict] = None

class DatasetOut(DatasetBase):
    """数据集输出"""
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True) 