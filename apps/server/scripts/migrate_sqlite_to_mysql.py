#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SQLite到MySQL数据迁移脚本

此脚本用于将数据从SQLite数据库迁移到MySQL数据库。
使用前请确保：
1. 已安装所需的依赖（pip install sqlalchemy pymysql）
2. 已创建MySQL数据库和用户
3. 环境变量中配置了正确的数据库连接URL
"""

import os
import sys
import logging
from sqlalchemy import create_engine, MetaData, Table, select, inspect

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

try:
    from apps.server.src.core.config import settings
    from apps.server.src.db.models import Base
except ImportError:
    logger.error("无法导入项目模块，请确保您在正确的目录中运行此脚本")
    sys.exit(1)

def get_sqlite_engine():
    """创建SQLite数据库引擎"""
    sqlite_url = f"sqlite:///{PROJECT_ROOT}/apps/server/ai_eval.db"
    return create_engine(sqlite_url)

def get_mysql_engine():
    """创建MySQL数据库引擎"""
    return create_engine(settings.db_url)

def migrate_data():
    """将数据从SQLite迁移到MySQL"""
    sqlite_engine = get_sqlite_engine()
    mysql_engine = get_mysql_engine()
    
    # 检查SQLite数据库是否存在
    if not os.path.exists(f"{PROJECT_ROOT}/apps/server/ai_eval.db"):
        logger.error("SQLite数据库文件不存在，无法进行迁移")
        return False
    
    # 创建MySQL表结构
    logger.info("在MySQL中创建表结构...")
    Base.metadata.create_all(mysql_engine)
    
    # 获取SQLite元数据
    sqlite_metadata = MetaData()
    sqlite_metadata.reflect(bind=sqlite_engine)
    
    # 获取MySQL检查器
    mysql_inspector = inspect(mysql_engine)
    
    # 遍历SQLite表并迁移数据
    for table_name in sqlite_metadata.tables:
        if table_name in Base.metadata.tables:
            logger.info(f"迁移表: {table_name}")
            
            # 获取表对象
            sqlite_table = Table(table_name, sqlite_metadata, autoload_with=sqlite_engine)
            mysql_table = Table(table_name, MetaData(), autoload_with=mysql_engine)
            
            # 获取表中的所有数据
            with sqlite_engine.connect() as sqlite_conn:
                data = sqlite_conn.execute(select(sqlite_table)).fetchall()
                
                if data:
                    logger.info(f"表 {table_name} 中找到 {len(data)} 条记录")
                    
                    # 将数据插入MySQL
                    with mysql_engine.begin() as mysql_conn:
                        # 检查表是否为空
                        count_query = select(mysql_table).limit(1)
                        if mysql_conn.execute(count_query).fetchone() is not None:
                            logger.warning(f"表 {table_name} 在MySQL中已有数据，跳过迁移")
                            continue
                        
                        # 获取列名
                        columns = [c.name for c in sqlite_table.columns]
                        
                        # 插入数据
                        for row in data:
                            row_dict = {columns[i]: value for i, value in enumerate(row)}
                            mysql_conn.execute(mysql_table.insert().values(**row_dict))
                        
                        logger.info(f"成功迁移表 {table_name} 的数据")
                else:
                    logger.info(f"表 {table_name} 中没有数据")
        else:
            logger.warning(f"表 {table_name} 在目标模型中不存在，跳过")
    
    logger.info("数据迁移完成")
    return True

if __name__ == "__main__":
    logger.info("开始从SQLite迁移到MySQL...")
    
    try:
        if migrate_data():
            logger.info("迁移成功完成！")
        else:
            logger.error("迁移失败")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"迁移过程中发生错误: {str(e)}")
        sys.exit(1) 