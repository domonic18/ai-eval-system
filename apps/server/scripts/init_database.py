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

def read_sql_file(file_path):
    """读取SQL文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    return sql_content

def init_database(drop_existing=False, sql_file=None):
    """初始化数据库"""
    # 加载环境变量
    load_dotenv()
    
    # 获取数据库连接信息
    db_host = os.getenv('MYSQL_HOST', '127.0.0.1')
    db_port = int(os.getenv('MYSQL_PORT', '3306'))
    db_user = os.getenv('MYSQL_USER', 'root')
    db_password = os.getenv('MYSQL_PASSWORD', 'abc123456')
    db_name = os.getenv('MYSQL_DB', 'ai_eval')
    
    # 连接到MySQL服务器（不指定数据库）
    try:
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        print(f"成功连接到MySQL服务器: {db_host}:{db_port}")
        
        # 如果需要删除现有数据库
        if drop_existing:
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            print(f"已删除现有数据库: {db_name}")
        
        # 创建数据库（如果不存在）
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"已创建数据库: {db_name}")
        
        # 选择数据库
        cursor.execute(f"USE {db_name}")
        
        # 根据SQL文件初始化数据库结构
        if sql_file is None:
            # 修复路径问题：使用正确的路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            sql_file = os.path.join(current_dir, 'database_init.sql')
        
        if not os.path.exists(sql_file):
            print(f"错误: SQL文件不存在: {sql_file}")
            return False
        
        # 读取SQL文件内容
        sql_content = read_sql_file(sql_file)
        
        # 分割SQL语句并执行
        statements = sql_content.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except Exception as e:
                    print(f"执行SQL语句时出错: {e}")
                    print(f"问题语句: {statement}")
        
        conn.commit()
        print("数据库初始化完成！")
        
        return True
    
    except Exception as e:
        print(f"数据库初始化过程中出错: {e}")
        return False
    
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI评测系统数据库初始化工具')
    parser.add_argument('--drop', action='store_true', help='删除现有数据库并重新创建')
    parser.add_argument('--sql', type=str, help='自定义SQL初始化文件路径')
    args = parser.parse_args()
    
    print("=== AI评测系统数据库初始化 ===")
    if args.drop:
        print("警告: 将删除现有数据库并重新创建")
        confirm = input("确定继续吗？[y/N]: ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
    
    success = init_database(drop_existing=args.drop, sql_file=args.sql)
    
    if success:
        print("数据库初始化成功！现在可以运行应用程序。")
    else:
        print("数据库初始化失败！请检查错误信息并重试。")
        sys.exit(1)

if __name__ == "__main__":
    main() 