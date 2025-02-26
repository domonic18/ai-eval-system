from fastapi import FastAPI
from dotenv import load_dotenv
import os
from apps.server.src.routers import eval
from apps.server.src.db import db
from apps.server.src.models import eval as eval_models
from apps.server.src.core.config import APP_NAME, settings

# 加载环境变量
load_dotenv()

# 确保数据库表结构一致
print("正在创建数据库表结构...")
db.create_tables()
print("✅ 数据库表结构已创建")

app = FastAPI(
    title=APP_NAME,
    description="基于OpenCompass的模型评测服务",
    version=settings.app_version
)

# 注册路由
app.include_router(eval.router, prefix=settings.api_prefix)

@app.get("/health")
async def health_check():
    return {"status": "ok"} 