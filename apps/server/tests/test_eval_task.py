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
    "model_name": "gpt-3.5-turbo",
    "dataset_name": "mmlu",
    "model_configuration": {
        "parameters": {"temperature": 0.7, "top_p": 0.9}
    },
    "dataset_configuration": {
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
        
        # 打印详细的响应信息
        print(f"\n响应状态码: {status_response.status_code}")
        print(f"响应头: {status_response.headers}")
        print(f"响应内容: {status_response.text}")
        
        # 尝试解析JSON，但添加错误处理
        try:
            status_data = status_response.json()
            print("\n当前任务状态:")
            print(f"ID: {status_data.get('id', 'N/A')}")
            print(f"状态: {status_data.get('status', 'N/A')}")
            print(f"任务ID: {status_data.get('task_id', 'N/A')}")
            print(f"进度: {status_data.get('progress', 0)}%")
            
            if status_data.get("error_message"):
                print(f"错误信息: {status_data.get('error_message')}")
            
            # 如果任务完成或失败，显示结果并退出
            if status_data.get("status") in ("completed", "failed"):
                if status_data.get("results"):
                    print("\n任务结果:")
                    print(json.dumps(status_data["results"], indent=2, ensure_ascii=False))
                break
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            # 如果无法解析JSON，等待一段时间后继续
            time.sleep(5)
            continue
            
        time.sleep(3)  # 等待3秒再查询
else:
    print("任务创建失败") 