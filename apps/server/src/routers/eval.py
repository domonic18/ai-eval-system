from fastapi import APIRouter, HTTPException, status, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from apps.server.src.db import get_db
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from apps.server.src.services.eval_service import create_evaluation_task, get_evaluation_status
from apps.server.src.tasks.opencompass_runner import get_runner
from typing import Dict, Any, List, Optional
import os
from pathlib import Path
import asyncio
from apps.server.src.models.eval import Evaluation, EvaluationStatus

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
    # 处理db可能是生成器的情况（FastAPI依赖注入）
    try:
        if hasattr(db, "__next__"):
            # db是一个生成器（来自FastAPI的Depends）
            db_session = next(db)
        else:
            # db是直接传入的Session对象
            db_session = db
            
        evaluations = db_session.query(Evaluation).all()
        result = []
        for eval_task in evaluations:
            progress = 0.0
            if eval_task.results and "progress" in eval_task.results:
                progress = eval_task.results["progress"]
            
            result.append({
                "id": eval_task.id,
                "model_name": eval_task.model_name,
                "dataset_name": eval_task.dataset_name,
                "status": eval_task.status,
                "progress": progress,
                "created_at": eval_task.created_at,
                "updated_at": eval_task.updated_at,
                "task_id": eval_task.task_id
            })
        
        return result
    finally:
        # 如果使用了生成器创建的会话，确保关闭它
        if 'db_session' in locals():
            db_session.close()

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

# 添加WebSocket端点
@router.websocket("/evaluations/{eval_id}/ws_logs")
async def websocket_logs(websocket: WebSocket, eval_id: int):
    """通过WebSocket提供实时日志"""
    await websocket.accept()
    
    try:
        # 获取评估任务信息
        db = next(get_db())
        eval_task = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
        
        if not eval_task:
            await websocket.send_json({"error": f"评估任务 {eval_id} 不存在"})
            await websocket.close()
            return
        
        # 查找日志文件
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
        logs_dir = os.path.join(BASE_DIR, "logs", "opencompass")
        
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
        
        log_pattern = f"eval_{eval_id}_*.log"
        
        log_files = list(Path(logs_dir).glob(log_pattern))
        if not log_files:
            await websocket.send_json({"info": f"任务 {eval_id} 的日志文件尚未创建，任务状态: {eval_task.status}"})
            
            # 如果任务正在运行，等待日志文件创建
            if eval_task.status == EvaluationStatus.RUNNING:
                await websocket.send_json({"info": "任务正在运行，等待日志文件创建..."})
                
                # 等待日志文件创建，最多等待30秒
                for _ in range(30):
                    await asyncio.sleep(1)
                    log_files = list(Path(logs_dir).glob(log_pattern))
                    if log_files:
                        break
                
                if not log_files:
                    await websocket.send_json({"error": "等待日志文件创建超时"})
                    await websocket.close()
                    return
            else:
                await websocket.send_json({"error": f"任务状态为 {eval_task.status}，没有日志文件"})
                await websocket.close()
                return
        
        # 获取最新的日志文件
        log_file = str(sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
        await websocket.send_json({"info": f"开始读取日志文件: {os.path.basename(log_file)}"})
        
        # 跟踪日志文件
        with open(log_file, 'r') as f:
            # 首先发送已有内容
            f.seek(0, 0)
            existing_content = f.read()
            if existing_content:
                lines = existing_content.strip().split('\n')
                for line in lines:
                    await websocket.send_text(line)
            
            # 移动到文件末尾
            f.seek(0, 2)
            
            # 持续监控新内容
            while True:
                # 检查任务是否已结束
                db_session = next(get_db())
                current_task = db_session.query(Evaluation).filter(Evaluation.id == eval_id).first()
                if current_task and current_task.status in [EvaluationStatus.COMPLETED, EvaluationStatus.FAILED]:
                    await websocket.send_json({"info": f"任务已{current_task.status}，日志流结束"})
                    break
                
                # 读取新行
                line = f.readline()
                if line:
                    await websocket.send_text(line.rstrip())
                else:
                    await asyncio.sleep(0.5)
                    
                # 释放数据库会话
                db_session.close()
    
    except WebSocketDisconnect:
        print(f"客户端断开WebSocket连接: {eval_id}")
    except Exception as e:
        print(f"WebSocket错误: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误详情: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"error": f"发生错误: {str(e)}"})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass 