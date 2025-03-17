import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from fastapi.security import OAuth2PasswordBearer
from api.routers import auth  
from api.routers import eval
from api.routers import model
from api.routers import dataset

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    docs_url="/api/docs",  # 自定义Swagger文档路径
    redoc_url=None         # 禁用Redoc文档
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"] 
)


# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(eval.router, prefix="/api/v1", tags=["评测"])
app.include_router(model.router, prefix="/api/v1", tags=["模型"])
app.include_router(dataset.router, prefix="/api/v1", tags=["数据集"])

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
