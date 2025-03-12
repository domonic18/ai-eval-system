from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from services.model_service import model_service
from api.deps import get_db
from schemas.auth import UserResponse
from schemas.model import ModelOut, ModelCreate, ModelUpdate
from services.auth_service import auth_service

router = APIRouter()

@router.get("/models", response_model=list[ModelOut])
def get_models(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return model_service.get_models(db)

@router.post("/models", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
def create_model(
    model_data: ModelCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return model_service.create_model(db, model_data, current_user.id)

@router.patch("/models/{model_id}", response_model=ModelOut)
def update_model(
    model_id: int,
    model_data: ModelUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return model_service.update_model(db, model_id, model_data, current_user.id)

@router.delete("/models/{model_id}")
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return model_service.delete_model(db, model_id, current_user.id) 