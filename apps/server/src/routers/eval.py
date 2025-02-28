from fastapi import APIRouter, HTTPException, status, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from apps.server.src.db import get_db
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from apps.server.src.services.eval_service import create_evaluation_task, get_evaluation_status, handle_websocket_logs
from apps.server.src.tasks.opencompass_runner import get_runner
from typing import Dict, Any, List, Optional
import os
from pathlib import Path
import asyncio
from apps.server.src.models.eval import Evaluation, EvaluationStatus
from apps.server.src.utils.redis_manager import RedisManager

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

@router.get("/evaluations", response_model=List[Dict[str, Any]])
async def list_evaluations(db: Session = Depends(get_db)):
    """获取所有评估任务列表"""
    try:
        # 更简单的直接使用db对象，不需要额外处理
        evaluations = db.query(Evaluation).all()
        result = []
        
        for eval_task in evaluations:
            # 安全处理progress字段
            progress = 0.0
            try:
                if eval_task.results:
                    # 如果results是字符串，尝试解析为字典
                    results_data = eval_task.results
                    if isinstance(results_data, str):
                        import json
                        results_data = json.loads(results_data)
                    
                    if isinstance(results_data, dict) and "progress" in results_data:
                        progress = float(results_data.get("progress", 0.0))
            except Exception as e:
                print(f"处理任务进度数据异常: {str(e)}")
                # 错误时使用默认值0.0
            
            # 构建响应数据
            result.append({
                "id": eval_task.id,
                "name": eval_task.name or f"评测任务-{eval_task.id}",  # 添加任务名称，如果为空则使用默认值
                "model_name": eval_task.model_name,
                "dataset_name": eval_task.dataset_name,
                "status": eval_task.status.upper() if eval_task.status else "UNKNOWN",  # 确保状态大写
                "progress": progress,
                "created_at": eval_task.created_at,
                "updated_at": eval_task.updated_at,
                "task_id": eval_task.task_id
            })
        
        return result
    except Exception as e:
        print(f"获取任务列表错误: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评估任务列表失败: {str(e)}"
        )
    # 不需要手动关闭会话，FastAPI会自动处理

@router.get("/evaluations/{eval_id}", response_model=EvaluationStatusResponse)
async def get_evaluation(eval_id: int, db: Session = Depends(get_db)):
    """获取评估任务详情
    
    Args:
        eval_id: 评估任务ID
        db: 数据库会话
        
    Returns:
        EvaluationStatusResponse: 评估任务状态详情
    """
    try:
        eval_status = await get_evaluation_status(eval_id, db)
        if eval_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"评估任务 {eval_id} 不存在"
            )
        return eval_status
    except Exception as e:
        print(f"获取任务详情错误: {str(e)}")
        import traceback
        traceback.print_exc()
        # 如果是已知的HTTPException，直接抛出
        if isinstance(e, HTTPException):
            raise
        # 否则转换为内部服务器错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评估任务详情失败: {str(e)}"
        )

@router.get("/evaluations/{eval_id}/logs", response_model=List[str])
async def get_evaluation_logs(eval_id: int, lines: Optional[int] = Query(50, description="获取的日志行数")):
    """获取评估任务的实时日志
    
    Args:
        eval_id: 评估任务ID
        lines: 要获取的日志行数，默认50行
        
    Returns:
        List[str]: 日志行列表
    """
    # 先从Redis获取日志
    logs = RedisManager.get_logs(eval_id, max_lines=lines)
    
    if logs:
        return logs
    
    # 如果Redis中没有日志，尝试从运行器获取
    runner = get_runner(f"eval_{eval_id}")
    if runner:
        return runner.get_recent_logs(lines)
    
    # 最后尝试从文件获取
    try:
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
        logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
        log_pattern = f"eval_{eval_id}_*.log"
        
        log_files = list(Path(logs_dir).glob(log_pattern))
        if log_files:
            log_file = str(sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
            with open(log_file, 'r') as f:
                all_lines = f.read().splitlines()
                # 获取最后n行
                log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                # 将日志添加到Redis
                for line in log_lines:
                    RedisManager.append_log(eval_id, line)
                    
                return log_lines
    except Exception as e:
        print(f"从文件读取日志失败: {str(e)}")
    
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

# 添加WebSocket端点
@router.websocket("/evaluations/{eval_id}/ws_logs")
async def websocket_logs(websocket: WebSocket, eval_id: int):
    """通过WebSocket提供实时日志
    
    Args:
        websocket: WebSocket连接
        eval_id: 评估任务ID
    """
    await websocket.accept()
    await handle_websocket_logs(websocket, eval_id)

# 添加删除评估任务接口
@router.delete("/evaluations/{eval_id}", response_model=Dict[str, Any])
async def delete_evaluation(eval_id: int, db: Session = Depends(get_db)):
    """删除评估任务
    
    Args:
        eval_id: 评估任务ID
        db: 数据库会话
        
    Returns:
        Dict[str, Any]: 操作结果
    """
    # 查询任务是否存在
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not eval_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"评估任务 {eval_id} 不存在"
        )
    
    try:
        # 如果任务正在运行，先尝试终止它
        if eval_task.status in [EvaluationStatus.PENDING.value, EvaluationStatus.RUNNING.value]:
            runner = get_runner(f"eval_{eval_id}")
            if runner and runner.is_running:
                runner.terminate()
        
        # 从数据库中删除任务
        db.delete(eval_task)
        db.commit()
        
        # 清理Redis中的数据
        try:
            RedisManager.delete_task_data(eval_id)
        except Exception as e:
            print(f"清理Redis数据出错: {str(e)}")
            # 继续执行，不影响主流程
        
        return {"success": True, "message": "任务已成功删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除任务失败: {str(e)}"
        )

# 添加更新任务名称接口
@router.patch("/evaluations/{eval_id}/name", response_model=Dict[str, Any])
async def update_evaluation_name(eval_id: int, name_data: Dict[str, str], db: Session = Depends(get_db)):
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
    
    # 查询任务是否存在
    eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    if not eval_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"评估任务 {eval_id} 不存在"
        )
    
    try:
        # 更新任务名称
        eval_task.name = name_data["name"].strip()
        db.commit()
        db.refresh(eval_task)
        
        # 同时更新Redis中的任务数据
        try:
            status_data = RedisManager.get_task_status(eval_id)
            if status_data:
                status_data["name"] = eval_task.name
                RedisManager.set_task_status(eval_id, status_data)
        except Exception as e:
            print(f"更新Redis数据出错: {str(e)}")
            # 继续执行，不影响主流程
        
        return {
            "success": True, 
            "message": "任务名称已更新",
            "name": eval_task.name
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新任务名称失败: {str(e)}"
        ) 