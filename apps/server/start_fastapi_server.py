# 启动FastAPI服务器
import os
import sys

# 设置环境变量
os.environ["DB_URL"] = "sqlite:///./ai_eval.db"

# 导入并运行服务
import uvicorn
from src.main import app

if __name__ == "__main__":
    print("启动FastAPI服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True) 