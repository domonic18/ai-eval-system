import requests

def test_evaluations_api():
    """测试评估任务列表API是否正常工作"""
    print('尝试向API请求任务列表...')
    try:
        response = requests.get('http://localhost:8000/api/v1/evaluations')
        print(f'API响应状态码: {response.status_code}')
        if response.status_code == 200:
            print('API测试成功!')
            data = response.json()
            print(f'获取到 {len(data.get("items", []))} 条评估任务')
        else:
            print(f'API响应错误: {response.text}')
    except Exception as e:
        print(f'发送请求时出错: {str(e)}')

if __name__ == '__main__':
    test_evaluations_api() 