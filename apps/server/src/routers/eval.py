from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from apps.server.src.db import get_db
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from apps.server.src.services.eval_service import create_evaluation_task, get_evaluation_status
from apps.server.src.tasks.opencompass_runner import get_runner
from typing import Dict, Any, List, Optional

router = APIRouter()

@router.post("/evaluations", 
             response_model=EvaluationResponse,
             status_code=status.HTTP_201_CREATED)
async def create_evaluation(eval_data: EvaluationCreate, db: Session = Depends(get_db)):
    try:
        return await create_evaluation_task(eval_data, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/evaluations/{eval_id}", response_model=EvaluationStatusResponse)
async def get_evaluation(eval_id: int, db: Session = Depends(get_db)):
    eval_status = await get_evaluation_status(eval_id, db)
    if eval_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"评估任务 {eval_id} 不存在"
        )
    return eval_status

@router.get("/evaluations/{eval_id}/logs", response_model=List[str])
async def get_evaluation_logs(eval_id: int, lines: Optional[int] = Query(50, description="获取的日志行数")):
    """获取评估任务的实时日志
    
    Args:
        eval_id: 评估任务ID
        lines: 要获取的日志行数，默认50行
        
    Returns:
        List[str]: 日志行列表
    """
    # 尝试从任务运行器获取日志
    runner = get_runner(f"eval_{eval_id}")
    if runner:
        return runner.get_recent_logs(lines)
    
    # 如果没有运行中的任务，则返回空列表
    return []

@router.post("/evaluations/{eval_id}/terminate", response_model=Dict[str, Any])
async def terminate_evaluation(eval_id: int, db: Session = Depends(get_db)):
    """终止评估任务
    
    Args:
        eval_id: 评估任务ID
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    # 检查任务是否存在
    eval_status = await get_evaluation_status(eval_id, db)
    if eval_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"评估任务 {eval_id} 不存在"
        )
    
    # 尝试终止任务
    runner = get_runner(f"eval_{eval_id}")
    if runner and runner.is_running:
        success = runner.terminate()
        if success:
            return {"success": True, "message": "任务已终止"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="终止任务失败"
            )
    
    # 任务不在运行
    return {"success": False, "message": "任务不在运行状态"} 