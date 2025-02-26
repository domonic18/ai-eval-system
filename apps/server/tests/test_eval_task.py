import requests
import json
import time
import os
import sys

# 添加项目根目录到Python路径
current_path = os.path.abspath(__file__)
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
sys.path.insert(0, root_path)
print(f"已添加项目根目录到Python路径: {root_path}")

base_url = "http://localhost:8000"

# 创建评估任务
payload = {
    "task_name": "测试完整评估流程",
    "model_configuration": {
        "model_name": "gpt-3.5-turbo",
        "parameters": {"temperature": 0.7, "top_p": 0.9}
    },
    "dataset_config": {
        "dataset_name": "mmlu",
        "split": "test",
        "subset": ["math", "computer_science"]
    }
}

# 创建任务
response = requests.post(
    f"{base_url}/api/v1/evaluations",
    data=json.dumps(payload),
    headers={"Content-Type": "application/json"}
)

print("任务创建响应:", response.json())

if response.status_code == 201:
    eval_id = response.json()["id"]
    
    # 轮询查询任务状态
    for _ in range(20):  # 最多查询20次
        status_response = requests.get(f"{base_url}/api/v1/evaluations/{eval_id}")
        status_data = status_response.json()
        
        print("\n当前任务状态:")
        print(f"状态: {status_data['status']}")
        print(f"Celery状态: {status_data['celery_status']}")
        print(f"进度: {status_data['progress']}%")
        print(f"消息: {status_data['message']}")
        
        if status_data["log_output"]:
            print("\n最新日志输出:")
            print(status_data["log_output"])
        
        # 如果任务完成或失败，显示结果并退出
        if status_data["status"] in ("completed", "failed"):
            if status_data["results"]:
                print("\n任务结果:")
                print(json.dumps(status_data["results"], indent=2, ensure_ascii=False))
            break
            
        time.sleep(3)  # 等待3秒再查询
else:
    print("任务创建失败") 