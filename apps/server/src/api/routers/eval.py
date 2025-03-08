from fastapi import APIRouter, HTTPException, status, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from api.deps import get_db
from schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from services.eval_service import (
    create_evaluation_task,
    get_evaluation_status, 
    handle_websocket_logs,
    list_evaluations,
    get_evaluation_logs,
    terminate_evaluation,
    delete_evaluation,
    update_evaluation_name
)
from typing import Dict, Any, List, Optional

router = APIRouter()

@router.post("/evaluations", 
             response_model=EvaluationResponse,
             status_code=status.HTTP_201_CREATED)
async def create_evaluation(eval_data: EvaluationCreate, db: Session = Depends(get_db)):
    """创建评估任务
    
    Args:
        eval_data: 评估数据
        db: 数据库会话
        
    Returns:
        EvaluationResponse: 评估响应
    """
    try:
        return await create_evaluation_task(eval_data, db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/evaluations", response_model=List[Dict[str, Any]])
def get_evaluations(db: Session = Depends(get_db)):
    """获取所有评估任务列表
    
    Args:
        db: 数据库会话
        
    Returns:
        List[Dict[str, Any]]: 评估任务列表
    """
    try:
        return list_evaluations(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评估任务列表失败: {str(e)}"
        )

@router.get("/evaluations/{eval_id}", response_model=EvaluationStatusResponse)
def get_evaluation(eval_id: int, db: Session = Depends(get_db)):
    """获取评估任务详情
    
    Args:
        eval_id: 评估任务ID
        db: 数据库会话
        
    Returns:
        EvaluationStatusResponse: 评估任务状态详情
    """
    try:
        eval_status = get_evaluation_status(eval_id, db)
        if eval_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"评估任务 {eval_id} 不存在"
            )
        return eval_status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评估任务详情失败: {str(e)}"
        )

@router.get("/evaluations/{eval_id}/logs", response_model=List[str])
def get_logs(eval_id: int, lines: Optional[int] = Query(50, description="获取的日志行数")):
    """获取评估任务的实时日志
    
    Args:
        eval_id: 评估任务ID
        lines: 要获取的日志行数，默认50行
        
    Returns:
        List[str]: 日志行列表
    """
    try:
        return get_evaluation_logs(eval_id, lines)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评估任务日志失败: {str(e)}"
        )

@router.post("/evaluations/{eval_id}/terminate", response_model=Dict[str, Any])
def terminate_eval(eval_id: int, db: Session = Depends(get_db)):
    """终止评估任务
    
    Args:
        eval_id: 评估任务ID
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        return terminate_evaluation(eval_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"终止评估任务失败: {str(e)}"
        )

@router.websocket("/evaluations/{eval_id}/ws_logs")
async def websocket_logs(websocket: WebSocket, eval_id: int):
    """通过WebSocket提供实时日志
    
    Args:
        websocket: WebSocket连接
        eval_id: 评估任务ID
    """
    await websocket.accept()
    await handle_websocket_logs(websocket, eval_id)

@router.delete("/evaluations/{eval_id}", response_model=Dict[str, Any])
def delete_eval(eval_id: int, db: Session = Depends(get_db)):
    """删除评估任务
    
    Args:
        eval_id: 评估任务ID
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    try:
        return delete_evaluation(eval_id, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除评估任务失败: {str(e)}"
        )

@router.patch("/evaluations/{eval_id}/name", response_model=Dict[str, Any])
def update_eval_name(eval_id: int, name_data: Dict[str, str], db: Session = Depends(get_db)):
    """更新评估任务名称
    
    Args:
        eval_id: 评估任务ID
        name_data: 包含新名称的数据 {"name": "新名称"}
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    # 验证请求数据
    if "name" not in name_data or not name_data["name"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供有效的任务名称"
        )
    
    try:
        return update_evaluation_name(eval_id, name_data["name"], db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新任务名称失败: {str(e)}"
        ) 