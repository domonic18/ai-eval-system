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

def main():
    """
    测试评估任务的异步工作流
    
    该脚本演示了评估任务的异步执行过程：
    1. 创建任务 - 任务立即返回，但在后台异步执行
    2. 获取任务状态 - 通过API获取当前执行状态
    """
    print("======== 异步评估任务测试 ========")
    print("注意: 任务将在后台异步执行，API请求会立即返回")
    
    # 创建评估任务
    payload = {
        "model_name": "hk33smarter_api",
        "dataset_name": "demo_cmmlu_chat_gen",
        "model_configuration": {
            "parameters": {"temperature": 0.7, "top_p": 0.9}
        },
        "dataset_configuration": {
            "split": "test"
        }
    }

    print("\n1. 提交评估任务（异步）")
    print("----------------------")
    # 创建任务
    response = requests.post(
        f"{base_url}/api/v1/evaluations",
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )

    if response.status_code != 201:
        print(f"任务创建失败: {response.text}")
        return

    # 解析响应
    task_data = response.json()
    eval_id = task_data["id"]
    print(f"任务创建成功! ID: {eval_id}")
    print(f"任务Celery ID: {task_data.get('task_id', 'N/A')}")
    print("任务已异步提交，正在后台执行...")
    
    # 等待用户决定是否查询状态
    user_input = input("\n是否查询任务执行状态? (y/n): ")
    if user_input.lower() != 'y':
        print("测试结束。您可以稍后通过API查询任务状态。")
        return
    
    print("\n2. 查询任务状态")
    print("----------------------")
    # 询问用户希望轮询多少次
    try:
        max_polls = int(input("轮询次数 (推荐5-10): ") or "5")
    except ValueError:
        max_polls = 5
    
    try:
        poll_interval = int(input("轮询间隔(秒) (推荐3-5): ") or "3")
    except ValueError:
        poll_interval = 3
    
    print(f"\n开始轮询任务状态 (每{poll_interval}秒一次，共{max_polls}次)...")
    
    # 轮询查询任务状态
    for i in range(max_polls):
        print(f"\n轮询 #{i+1}:")
        status_response = requests.get(f"{base_url}/api/v1/evaluations/{eval_id}")
        
        # 尝试解析JSON，但添加错误处理
        try:
            status_data = status_response.json()
            print(f"任务状态: {status_data.get('status', 'N/A')}")
            print(f"进度: {status_data.get('progress', 0)}%")
            
            if status_data.get("error_message"):
                print(f"错误信息: {status_data.get('error_message')}")
            
            # 如果任务完成或失败，显示结果并退出
            if status_data.get("status") in ("completed", "failed"):
                print("\n任务已完成!")
                if status_data.get("results"):
                    print("\n任务结果:")
                    print(json.dumps(status_data["results"], indent=2, ensure_ascii=False))
                break
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            # 如果无法解析JSON，等待一段时间后继续
            time.sleep(poll_interval)
            continue
            
        # 提示用户任务正在后台执行
        if i == max_polls - 1:
            print("\n轮询完成。任务仍在后台执行中...")
            print(f"您可以稍后通过API继续查询: GET {base_url}/api/v1/evaluations/{eval_id}")
            print("或者使用WebSocket实时获取日志: WebSocket连接到 {base_url}/api/v1/evaluations/{eval_id}/ws_logs")
        else:
            print(f"等待{poll_interval}秒后再次查询...")
            time.sleep(poll_interval)
    
    # 提醒用户可以使用日志API
    print("\n3. 查看任务日志")
    print("----------------------")
    print(f"使用以下命令查看实时日志:")
    print(f"1. API方式: curl {base_url}/api/v1/evaluations/{eval_id}/logs")
    print(f"2. WebSocket方式: 使用WebSocket客户端连接到 ws://{base_url.replace('http://', '')}/api/v1/evaluations/{eval_id}/ws_logs")
    print(f"3. 测试工具: python apps/server/tests/test_logs_api.py {eval_id}")
    
    print("\n======== 测试完成 ========")

if __name__ == "__main__":
    main() 