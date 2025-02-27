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

def get_evaluation_logs(eval_id, lines=50):
    """获取评估任务的日志"""
    response = requests.get(f"{base_url}/api/v1/evaluations/{eval_id}/logs?lines={lines}")
    
    # 打印请求信息
    print(f"请求URL: {response.url}")
    print(f"状态码: {response.status_code}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取日志失败: {response.text}")
        return []

def poll_logs(eval_id, interval=5, duration=60):
    """定期轮询日志"""
    start_time = time.time()
    last_log_count = 0
    
    while time.time() - start_time < duration:
        logs = get_evaluation_logs(eval_id)
        
        if len(logs) > last_log_count:
            # 只打印新增的日志
            new_logs = logs[last_log_count:]
            print("\n新增日志:")
            for log in new_logs:
                print(f"  {log}")
            
            last_log_count = len(logs)
        
        time.sleep(interval)

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("用法: python test_logs_api.py <评估任务ID> [轮询间隔(秒)] [轮询时长(秒)]")
        sys.exit(1)
    
    eval_id = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    print(f"开始轮询评估任务 {eval_id} 的日志...")
    print(f"轮询间隔: {interval}秒, 持续时间: {duration}秒")
    
    poll_logs(eval_id, interval, duration) 