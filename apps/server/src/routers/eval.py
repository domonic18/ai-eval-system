from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from apps.server.src.db import get_db
from apps.server.src.schemas.eval import EvaluationCreate, EvaluationResponse, EvaluationStatusResponse
from apps.server.src.services.eval_service import create_evaluation_task, get_evaluation_status

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

@router.get("/evaluations/{eval_id}", 
            response_model=EvaluationStatusResponse)
async def get_evaluation(eval_id: int, db: Session = Depends(get_db)):
    eval_status = await get_evaluation_status(eval_id, db)
    if not eval_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"评估任务 ID {eval_id} 不存在"
        )
    return eval_status 