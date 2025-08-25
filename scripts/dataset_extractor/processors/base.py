#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集处理器基础抽象类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import sys
import os

# 添加父目录到路径以导入config模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_output_dir, get_dataset_config


class BaseDatasetProcessor(ABC):
    """数据集处理器抽象基类"""
    
    def __init__(self, dataset_name: str):
        """
        初始化数据集处理器
        
        Args:
            dataset_name: 数据集名称
        """
        self.dataset_name = dataset_name
        self.config = get_dataset_config(dataset_name)
        self.output_dir = get_output_dir(dataset_name)
        
        print(f"✅ 初始化 {self.config['name']} 数据集处理器")
        print(f"📁 输出目录: {self.output_dir.absolute()}")
    
    @abstractmethod
    def process(self, **kwargs) -> bool:
        """
        处理数据集的主要方法
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def find_data_path(self) -> Optional[str]:
        """
        查找数据文件路径
        
        Returns:
            str: 找到的数据路径，如果未找到则返回None
        """
        pass
    
    def save_to_excel(self, data: List[Dict], filename: str, sheet_name: str = "Sheet1") -> bool:
        """
        保存数据到Excel文件
        
        Args:
            data: 数据列表
            filename: 文件名
            sheet_name: 工作表名称
            
        Returns:
            bool: 是否成功
        """
        try:
            if not data:
                print(f"⚠️  没有数据可保存到 {filename}")
                return False
                
            df = pd.DataFrame(data)
            filepath = self.output_dir / filename
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"✅ Excel文件保存成功: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ 保存Excel文件失败: {e}")
            return False
    
    def save_to_csv(self, data: List[Dict], filename: str) -> bool:
        """
        保存数据到CSV文件
        
        Args:
            data: 数据列表
            filename: 文件名
            
        Returns:
            bool: 是否成功
        """
        try:
            if not data:
                print(f"⚠️  没有数据可保存到 {filename}")
                return False
                
            df = pd.DataFrame(data)
            filepath = self.output_dir / filename
            
            df.to_csv(filepath, index=False, encoding='utf-8')
            return True
            
        except Exception as e:
            print(f"❌ 保存CSV文件失败: {e}")
            return False
    
    def _find_data_path_from_config(self) -> Optional[str]:
        """
        从配置中查找数据路径
        
        Returns:
            str: 找到的数据路径，如果未找到则返回None
        """
        import os
        
        for path in self.config["paths"]:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
        return None
