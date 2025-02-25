# 调试模式启动FastAPI服务器
import os
# 设置环境变量强制使用SQLite
os.environ["DB_URL"] = "sqlite:///./ai_eval.db"

import debugpy
debugpy.listen(("0.0.0.0", 5678))
print("等待调试器连接...")
debugpy.wait_for_client()
print("调试器已连接！")

import uvicorn
from src.main import app

if __name__ == "__main__":
    print("调试模式启动FastAPI服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False) 