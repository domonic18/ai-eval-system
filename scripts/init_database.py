#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库初始化脚本
用于快速初始化AI评测系统的数据库
"""

import os
import sys
import pymysql
import argparse
from dotenv import load_dotenv
import time
import glob

def get_sql_files():
    """获取按顺序排序的SQL文件"""
    # 获取脚本所在目录的父目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    initdb_dir = os.path.join(parent_dir, 'initdb')
    
    # 查找所有.sql文件并按文件名排序
    sql_files = glob.glob(os.path.join(initdb_dir, '*.sql'))
    sql_files.sort(key=lambda x: os.path.basename(x))
    
    # 验证必须的初始化文件
    required_files = ['01_create_database.sql', '02_create_tables.sql', '03_insert_data.sql']
    for f in required_files:
        if not os.path.exists(os.path.join(initdb_dir, f)):
            raise FileNotFoundError(f"缺少必要的SQL文件: {f}")
    
    return sql_files

def execute_sql_files(cursor, sql_files):
    """按顺序执行SQL文件"""
    for file_path in sql_files:
        print(f"\n正在执行SQL文件: {os.path.basename(file_path)}")
        
        # 读取SQL文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割并执行SQL语句
        statements = sql_content.split(';')
        for i, statement in enumerate(statements, 1):
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                    print(f"  执行第 {i} 条语句成功")
                except pymysql.Error as e:
                    print(f"  错误：执行第 {i} 条语句失败 - {e}")
                    print(f"  问题语句: {statement[:100]}...")  # 显示前100个字符
                    raise

def init_database(drop_existing=False):
    """初始化数据库"""
    # 加载环境变量
    load_dotenv()
    
    # 获取数据库连接信息
    db_host = os.getenv('MYSQL_HOST', 'mysql')
    db_port = int(os.getenv('MYSQL_PORT', '3306'))
    db_user = os.getenv('MYSQL_USER', 'root')
    db_password = os.getenv('MYSQL_PASSWORD', 'abc123456')
    db_name = os.getenv('MYSQL_DB', 'ai_eval')
    
    # 获取排序后的SQL文件
    try:
        sql_files = get_sql_files()
        print("找到以下SQL文件:")
        for f in sql_files:
            print(f"  - {os.path.basename(f)}")
    except Exception as e:
        print(f"获取SQL文件失败: {e}")
        return False

    # 数据库连接重试逻辑
    max_retries = 5
    for attempt in range(max_retries):
        try:
            conn = pymysql.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                charset='utf8mb4'
            )
            cursor = conn.cursor()
            print(f"\n成功连接到MySQL服务器: {db_host}:{db_port}")
            
            # 删除现有数据库（如果需要）
            if drop_existing:
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
                print(f"已删除现有数据库: {db_name}")
            
            # 创建新数据库
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"已创建数据库: {db_name}")
            cursor.execute(f"USE {db_name}")
            
            # 按顺序执行SQL文件
            execute_sql_files(cursor, sql_files)
            
            conn.commit()
            print("\n数据库初始化完成！")
            return True
            
        except pymysql.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"数据库连接失败，重试中 ({attempt+1}/{max_retries})...")
                time.sleep(5)
            else:
                print(f"数据库连接失败: {e}")
                return False
        finally:
            if 'conn' in locals() and conn.open:
                conn.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI评测系统数据库初始化工具')
    parser.add_argument('--drop', action='store_true', help='删除现有数据库并重新创建')
    args = parser.parse_args()
    
    print("=== AI评测系统数据库初始化 ===")
    if args.drop:
        print("警告: 将删除现有数据库并重新创建")
        confirm = input("确定继续吗？[y/N]: ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
    
    success = init_database(drop_existing=args.drop)
    
    if success:
        print("数据库初始化成功！现在可以运行应用程序。")
    else:
        print("数据库初始化失败！请检查错误信息并重试。")
        sys.exit(1)

if __name__ == "__main__":
    main() 