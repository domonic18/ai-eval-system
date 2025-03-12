from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any, List, Union

class EvaluationBase(BaseModel):
    task_name: str
    model_configuration: dict
    dataset_config: dict


class EvaluationCreate(BaseModel):
    """评估创建请求模式"""
    model_name: str = Field(..., description="要评估的模型名称")
    dataset_names: List[str] = Field(..., description="要使用的数据集名称")
    model_configuration: Union[Dict[str, Any], str] = Field(default={}, description="模型的配置信息")
    dataset_configuration: Union[Dict[str, Any], str] = Field(default={}, description="数据集的配置信息")
    eval_config: Optional[Dict[str, Any]] = Field(default={}, description="评估的配置信息")    
    model_config = ConfigDict(
        populate_by_name=True,
        extra='allow'
    )
    env_vars: Optional[Dict[str, Any]] = Field(default={}, description="环境变量（API_URL/API_KEY等）")


class EvaluationResponse(BaseModel):
    """评估响应模式"""
    id: int = Field(..., description="评估任务ID")
    model_name: str = Field(..., description="模型名称")
    dataset_names: str = Field(..., description="数据集名称")
    status: str = Field(..., description="评估任务状态")
    task_id: Optional[str] = Field(None, description="Celery 任务ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

class EvaluationStatusResponse(BaseModel):
    """评估状态响应"""
    id: int
    model_name: str
    dataset_names: str
    status: str
    progress: float = 0.0
    created_at: datetime
    updated_at: Optional[datetime] = None
    task_id: Optional[str] = None
    error_message: Optional[str] = Field(None, description="错误信息")
    results: Optional[Dict[str, Any]] = Field(None, description="评估结果")
    details: Dict[str, Any] = Field(default={}, description="详细信息")

class OpenCompassConfig(BaseModel):
    """OpenCompass 配置模式"""
    model_name: str = Field(..., description="模型名称")
    model_path: Optional[str] = Field(None, description="模型路径")
    model_type: str = Field("huggingface", description="模型类型")
    dataset_names: str = Field(..., description="数据集名称")
    dataset_path: Optional[str] = Field(None, description="数据集路径")
    output_path: Optional[str] = Field("outputs/default", description="输出路径")
    api_key: Optional[str] = Field(None, description="API 密钥")
    api_base: Optional[str] = Field(None, description="API 基础URL")
    parameters: Optional[Dict[str, Any]] = Field(None, description="模型参数")
    max_seq_len: Optional[int] = Field(None, description="最大序列长度")
    batch_size: Optional[int] = Field(None, description="批处理大小")

class LogQueryParams(BaseModel):
    """日志查询参数"""
    lines: Optional[int] = Field(50, description="要获取的日志行数")
    from_line: Optional[int] = Field(0, description="起始行号")

class LogResponse(BaseModel):
    """日志响应模式"""
    logs: List[str] = Field(..., description="日志行列表")
    total_lines: int = Field(..., description="总行数")
    has_more: bool = Field(..., description="是否有更多日志") 

class DatasetResult(BaseModel):
    dataset: str
    accuracy: float
    prediction_path: Optional[str]

class ModelResult(BaseModel):
    model_name: str
    datasets: List[DatasetResult]

class EvaluationResultResponse(BaseModel):
    results: List[ModelResult]
    summary: List[dict]
    download_url: str