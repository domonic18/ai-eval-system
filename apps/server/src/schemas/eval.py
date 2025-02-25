from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any

class EvaluationBase(BaseModel):
    task_name: str
    model_configuration: dict
    dataset_config: dict

class EvaluationCreate(EvaluationBase):
    pass

class EvaluationResponse(EvaluationBase):
    id: int
    status: str
    celery_task_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class EvaluationStatusResponse(BaseModel):
    id: int
    task_name: str
    status: str
    celery_status: Optional[str] = None
    progress: float = 0
    message: str = ""
    log_output: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) 