from tasks.runners.runner_base import create_runner
from tasks.runners.runner_enhanced import EnhancedRunner
from tasks.runners.env_manager import EnvManager
from core.config import BASE_DIR
from core.config import settings
from schemas.eval import EvaluationCreate
from pathlib import Path
import os


def collect_results() -> dict:
    print("收集评估结果")
    return {}

def test_command_injection():
    env_mgr = EnvManager(123)
    env_mgr.load_env_json({"API_KEY": "sk-test", "MODEL": "gpt-4"})
    
    runner = EnhancedRunner(123)
    eval_data = EvaluationCreate(
        model_name="hk33smarter_api",
        dataset_name=["math_eval", "code_analysis"],
        eval_config={"debug": True}
    )
    cmd = runner.build_command(eval_data)
    
    assert "API_KEY='sk-test'" in cmd
    assert "--datasets math_eval code_analysis" in cmd
    assert "--debug" in cmd

# 测试多数据集场景
def test_multiple_datasets():
    runner = EnhancedRunner(123)
    eval_data = EvaluationCreate(
        model_name="test_model",
        dataset_name=["dataset1", "dataset2"],
        eval_config={"debug": True}
    )
    cmd = runner.build_command(eval_data)
    assert "--datasets dataset1 dataset2" in cmd


def test_runner_script():
    env_vars = {
       "API_KEY": "sk-8B8KptRvxQnPTVsH7665380d95A748F7BcAdA3E4279c6bAe",
       "API_BASE": "https://guanghua-api.hk33smarter.com/v1",
       "MODEL": "Qwen/qwen2-1.5b-instruct"
    }
    eval_data = EvaluationCreate(
        model_name="hk33smarter_api",
        dataset_name=["demo_math_chat_gen", "demo_gsm8k_chat_gen"],
        eval_config={"debug": True}
    )

    eval_id = 109
    work_dir = os.path.join(BASE_DIR, "logs", "test_runner_script")


    # 1. 初始化增强型执行器
    runner = EnhancedRunner(
        eval_id=eval_id,
        working_dir=work_dir,  # 从配置获取工作目录
        opencompass_path=settings.opencompass_path
    )
    
    # 2. 配置环境变量
    runner.env_manager.load_env_json(env_vars)
    
    # 3. 执行任务
    exit_code = runner.execute(eval_data)
    
    # 5. 结果处理
    if exit_code == 0:
        return {"status": "success", "exit_code": exit_code}
    else:
        return {"status": "failed", "exit_code": exit_code}


if __name__ == "__main__":
    #test_runner()
    test_runner_script()