# from fastapi import FastAPI, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from fastapi.middleware.cors import CORSMiddleware
# from apps.server.src.services.auth_service import auth_service
# from sqlalchemy.orm import Session
# import logging
# from pathlib import Path

# # 配置日志
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # 创建应用
# app = FastAPI(title="AI评测系统", description="AI模型评测系统API")

# # CORS中间件
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # 允许所有来源，生产环境应该限制
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 注册路由
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
# app.include_router(eval.router, prefix="/api/v1", tags=["评测"])

# # 获取令牌依赖
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# # 当前用户依赖
# def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
#     user = auth_service.get_current_user(db, token)
#     if user is None:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="无效的凭证",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return user

# # 启动事件
# @app.on_event("startup")
# async def startup_event():
#     # 创建数据库表
#     Base.metadata.create_all(bind=engine)
    
#     # 确保日志目录存在
#     logs_dir = Path("logs/opencompass")
#     logs_dir.mkdir(parents=True, exist_ok=True)
    
#     # 启动日志同步服务
#     start_log_sync()
    
#     print("应用已启动")

# # 关闭事件
# @app.on_event("shutdown")
# async def shutdown_event():
#     # 停止日志同步服务
#     stop_log_sync()
    
#     print("应用已关闭")

# # 健康检查
# @app.get("/health")
# def health_check():
#     return {"status": "ok"} 



# main.py

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import settings
from core.database import engine, Base
from core.database import Base
from fastapi.security import OAuth2PasswordBearer
from api.routers import auth  # 导入你的路由模块
from api.routers import eval  # 添加这行导入语句

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """应用生命周期管理"""
#     # 启动时执行
#     logger.info("Creating database tables...")
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
    
#     yield  # 这里保持应用运行
    
#     # 关闭时执行
#     logger.info("Closing database connections...")
#     await engine.dispose()

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    # lifespan=lifespan,
    docs_url="/api/docs",  # 自定义Swagger文档路径
    redoc_url=None         # 禁用Redoc文档
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.CORS_ORIGINS,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # 包含路由模块
# app.include_router(
#     auth.router,
#     prefix="/api/auth",  # 统一添加路由前缀
#     tags=["认证"]
# )

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(eval.router, prefix="/api/v1", tags=["评测"])

# 获取令牌依赖
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 健康检查端点
@app.get("/api/healthcheck")
async def health_check():
    return {"status": "healthy"}

# 开发模式下直接运行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
