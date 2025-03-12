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
        "celery",
        "-A", "celery_app:celery_app",
        "worker",
        "--loglevel=DEBUG",
        "--concurrency=1",
        "--pool=prefork",
        "-Q", "eval_tasks"
    ]

    try:
        print(f"🔧 正在启动 Celery 工作进程...")
        subprocess.run(command, check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"❌ 工作进程启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 工作进程已停止")

if __name__ == "__main__":
    main()
