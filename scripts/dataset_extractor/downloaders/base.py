#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集下载器基础抽象类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import sys
import os

# 添加父目录到路径以导入config模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_cache_dir, get_dataset_config


class BaseDatasetDownloader(ABC):
    """数据集下载器抽象基类"""
    
    def __init__(self):
        """初始化下载器"""
        self.cache_dir = get_cache_dir()
        print(f"缓存目录: {self.cache_dir.absolute()}")
    
    @abstractmethod
    def download_dataset(self, dataset_name: str) -> bool:
        """
        下载指定的数据集
        
        Args:
            dataset_name: 数据集名称
            
        Returns:
            bool: 是否下载成功
        """
        pass
    
    def _get_dataset_config(self, dataset_name: str) -> dict:
        """获取数据集配置"""
        return get_dataset_config(dataset_name)
    
    def _get_cache_dir(self) -> Path:
        """获取缓存目录"""
        return self.cache_dir
