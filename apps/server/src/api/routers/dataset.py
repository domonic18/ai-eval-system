from api.deps import get_db
from sqlalchemy.orm import Session
from schemas.auth import UserResponse
from schemas.dataset import DatasetOut, DatasetCreate, DatasetUpdate
from fastapi import APIRouter, Depends, status
from services.auth_service import auth_service
from services.dataset_service import dataset_service

router = APIRouter()

@router.get("/datasets", response_model=list[DatasetOut])
def get_datasets(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return dataset_service.get_datasets(db)

@router.post("/datasets", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(
    dataset_data: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return dataset_service.create_dataset(db, dataset_data, current_user.id)

@router.patch("/datasets/{dataset_id}", response_model=DatasetOut)
def update_dataset(
    dataset_id: int,
    dataset_data: DatasetUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return dataset_service.update_dataset(db, dataset_id, dataset_data, current_user.id)

@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(auth_service.get_current_user)
):
    return dataset_service.delete_dataset(db, dataset_id, current_user.id) 