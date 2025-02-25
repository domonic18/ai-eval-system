# 调试模式启动Celery Worker
import os
import sys
import debugpy

# 设置环境变量
os.environ["DB_URL"] = "sqlite:///./ai_eval.db"

# 启动调试服务器
debugpy.listen(("0.0.0.0", 5679))  # 注意：使用不同的端口避免与API服务器冲突
print("等待调试器连接到Celery Worker...")
debugpy.wait_for_client()
print("调试器已连接到Celery Worker！")

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# 显式导入任务模块以确保任务被注册
from apps.server.src.tasks import eval_tasks

# 导入celery应用
from apps.server.src.celery_app import celery_app

print("调试模式启动Celery Worker...")
print("加载的任务:", celery_app.tasks.keys())

# 在这里可以设置断点
# breakpoint()

if __name__ == "__main__":
    argv = [
        'worker',
        '--loglevel=INFO',
        # 单进程模式，更适合调试
        '--concurrency=1',
        # 禁用预取，确保任务一个一个处理
        '--prefetch-multiplier=1'
    ]
    celery_app.worker_main(argv) 