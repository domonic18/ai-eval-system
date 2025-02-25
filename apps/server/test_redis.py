import redis

r = redis.Redis(host='localhost', port=6379, db=0)
try:
    r.ping()
    print("连接到Redis成功!")
    r.set('test_key', 'test_value')
    print("存储值:", r.get('test_key'))
except Exception as e:
    print(f"连接Redis失败: {e}") 