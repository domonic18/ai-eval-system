#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def main():
    # 设置项目根目录
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + (f":{env['PYTHONPATH']}" if "PYTHONPATH" in env else "")

    # 启动命令参数
    command = [
        "uvicorn",
        "apps.server.src.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]

    try:
        print(f"🚀 正在启动 FastAPI 服务（开发模式）...")
        subprocess.run(command, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")

if __name__ == "__main__":
    main()
