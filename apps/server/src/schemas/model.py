from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class ModelBase(BaseModel):
    """模型基类"""
    name: str
    provider: str
    model_type: str
    description: Optional[str] = None
    version: Optional[str] = None
    configuration: Optional[dict] = None
    is_public: bool = True

class ModelCreate(ModelBase):
    pass

class ModelUpdate(BaseModel):
    """模型更新结构"""
    description: Optional[str] = None
    version: Optional[str] = None
    configuration: Optional[dict] = None
    is_public: Optional[bool] = None

class ModelOut(ModelBase):
    """模型输出"""
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
