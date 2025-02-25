from fastapi import FastAPI
from dotenv import load_dotenv
import os
from .routers import eval
from .database import engine
from .models import eval as eval_models

# 加载环境变量
load_dotenv()

# 确保数据库表结构一致
eval_models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI评测系统后端",
    description="基于OpenCompass的模型评测服务",
    version="0.1.0"
)

# 注册路由
app.include_router(eval.router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"} 