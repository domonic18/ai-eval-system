from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from apps.server.src.db import engine, Base, SessionLocal, get_db
from apps.server.src.routers import eval, auth
from apps.server.src.services.auth_service import auth_service
from apps.server.src.tasks.log_sync import start_log_sync, stop_log_sync
from sqlalchemy.orm import Session
import logging
# import os
from pathlib import Path
# import sys

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建应用
app = FastAPI(title="AI评测系统", description="AI模型评测系统API")

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(eval.router, prefix="/api/v1", tags=["评测"])

# 获取令牌依赖
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 当前用户依赖
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth_service.get_current_user(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# 启动事件
@app.on_event("startup")
async def startup_event():
    # 创建数据库表
    Base.metadata.create_all(bind=engine)
    
    # 确保日志目录存在
    logs_dir = Path("logs/opencompass")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # 启动日志同步服务
    start_log_sync()
    
    print("应用已启动")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    # 停止日志同步服务
    stop_log_sync()
    
    print("应用已关闭")

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "ok"} 