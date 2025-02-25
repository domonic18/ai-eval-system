# 导入所有任务以确保Celery可以发现它们
from .eval_tasks import run_evaluation

# 打印一条信息确认导入
print(f"已加载评估任务: {run_evaluation.name}")
