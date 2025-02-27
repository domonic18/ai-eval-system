# 启动FastAPI服务器
import os
import sys

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# 导入并运行服务
import uvicorn

if __name__ == "__main__":
    print("启动FastAPI服务器...")
    # 使用模块路径启动，支持热重载
    uvicorn.run("apps.server.src.main:app", host="0.0.0.0", port=8000, reload=True) 