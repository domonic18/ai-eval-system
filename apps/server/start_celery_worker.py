# 启动Celery Worker服务
import os
import sys
import importlib

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, project_root)

# 显式导入任务模块以确保任务被注册
from apps.server.src.tasks import eval_tasks

# 从apps.server导入celery应用
from apps.server.src.celery_app import celery_app

print("启动Celery Worker服务...")
print("加载的任务:", celery_app.tasks.keys())
print("eval_tasks模块中的任务:", eval_tasks.run_evaluation.name)

if __name__ == "__main__":
    # 尝试重新导入一次任务模块
    importlib.reload(eval_tasks)
    
    print("重新加载后的任务:", celery_app.tasks.keys())
    
    argv = [
        'worker',
        '--loglevel=INFO',
    ]
    celery_app.worker_main(argv) 