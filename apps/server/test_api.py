import requests
import json

# 测试健康检查
response = requests.get("http://localhost:8000/health")
print("健康检查响应:", response.json())

# 测试创建评估任务
payload = {
    "task_name": "Python测试任务",
    "model_configuration": {
        "model_name": "gpt-3.5-turbo",
        "parameters": {"temperature": 0.7}
    },
    "dataset_config": {
        "dataset_name": "mmlu",
        "split": "test"
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/evaluations",
    data=json.dumps(payload),
    headers={"Content-Type": "application/json"}
)

print("创建评估任务响应:", response.json()) 