#!/usr/bin/env python3
# 测试数据库连接脚本

# 添加项目根目录到Python路径
import os
import sys
import traceback
from urllib import parse

# 获取当前文件的绝对路径
current_path = os.path.abspath(__file__)
# 获取项目根目录路径（向上3级）
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
# 将项目根目录添加到Python路径
sys.path.insert(0, root_path)
print(f"已添加项目根目录到Python路径: {root_path}")

# 导入必要的模块
try:
    # 先导入环境变量
    from dotenv import load_dotenv
    load_dotenv(os.path.join(root_path, "apps", "server", ".env"))
    
    # 打印环境变量
    print(f"DB_URL环境变量: {os.getenv('DB_URL')}")
    print(f"MYSQL_HOST环境变量: {os.getenv('MYSQL_HOST')}")
    print(f"MYSQL_USER环境变量: {os.getenv('MYSQL_USER')}")
    print(f"MYSQL_PASSWORD环境变量: {os.getenv('MYSQL_PASSWORD')}")
    
    # 导入数据库模块
    print("尝试导入数据库模块...")
    from apps.server.src.db import SessionLocal, db
    from apps.server.src.models.eval import Evaluation, EvaluationStatus
    
    print(f"成功导入数据库模块，数据库URL: {db.DATABASE_URL}")
    
    # 尝试连接数据库
    print("尝试连接数据库...")
    session = SessionLocal()
    print("数据库连接成功!")
    
    # 创建表结构
    print("尝试创建表结构...")
    db.create_tables()
    
    # 尝试插入记录
    print("尝试插入测试记录...")
    test_eval = Evaluation(
        task_name="测试数据库连接",
        model_configuration={"model_name": "test-model"},
        dataset_config={"dataset_name": "test-dataset"},
        status=EvaluationStatus.PENDING
    )
    
    session.add(test_eval)
    print("已添加记录到会话")
    
    session.commit()
    print("已提交事务")
    
    session.refresh(test_eval)
    print(f"测试记录创建成功，ID: {test_eval.id}")
    
    # 查询记录
    result = session.query(Evaluation).filter_by(id=test_eval.id).first()
    print(f"查询结果: {result.task_name}, 状态: {result.status}")
    
    print("数据库测试完成!")
    
except Exception as e:
    print(f"发生错误: {str(e)}")
    traceback.print_exc() 