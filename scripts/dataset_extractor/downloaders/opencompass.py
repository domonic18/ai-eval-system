#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
OpenCompass数据集下载器
"""

import os
import sys
from pathlib import Path

# 添加父目录到路径以导入config模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    DATASET_IDS, EXPECTED_DATA_STRUCTURE,
    ENV_COMPASS_DATA_CACHE,
    ERROR_MESSAGES, SUCCESS_MESSAGES, INFO_MESSAGES
)
from downloaders.base import BaseDatasetDownloader


class OpenCompassDownloader(BaseDatasetDownloader):
    """OpenCompass数据集下载器"""
    
    def __init__(self):
        super().__init__()
    
    def download_dataset(self, dataset_name: str) -> bool:
        """
        下载指定的数据集
        
        Args:
            dataset_name: 数据集名称
            
        Returns:
            bool: 是否下载成功
        """
        if dataset_name not in DATASET_IDS:
            print(ERROR_MESSAGES["dataset_not_supported"].format(dataset_name))
            return False
        
        dataset_config = self._get_dataset_config(dataset_name)
        dataset_id = DATASET_IDS[dataset_name]
        
        print(INFO_MESSAGES["start_download"].format(dataset_config["name"]))
        print(INFO_MESSAGES["cache_dir"].format(self.cache_dir.absolute()))
        print(INFO_MESSAGES["dataset_path"].format(dataset_id))
        
        try:
            # 设置环境变量
            os.environ[ENV_COMPASS_DATA_CACHE] = str(self.cache_dir.absolute())
            
            # 尝试导入OpenCompass模块
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs" / "OpenCompass"))
                from opencompass.utils import get_data_path
                OPENCOMPASS_AVAILABLE = True
            except ImportError:
                print(ERROR_MESSAGES["module_unavailable"])
                return False
            
            # 触发下载
            data_path = get_data_path(dataset_id, local_mode=False)
            print(INFO_MESSAGES["dataset_path"].format(data_path))
            
            # 检查是否下载成功
            expected_path = self.cache_dir / EXPECTED_DATA_STRUCTURE[dataset_name]
            if expected_path.exists():
                print(SUCCESS_MESSAGES["download_success"].format(dataset_config["name"]))
                print(SUCCESS_MESSAGES["data_location"].format(expected_path.absolute()))
                return True
            else:
                print(ERROR_MESSAGES["download_may_failed"])
                return False
                
        except Exception as e:
            print(ERROR_MESSAGES["download_failed"].format(str(e)))
            return False
