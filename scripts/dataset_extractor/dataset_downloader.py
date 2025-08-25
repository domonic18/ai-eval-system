#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集下载工具
支持通过ModelScope下载OpenCompass数据集
"""

import os
import sys
import argparse
from pathlib import Path

# ==================== 配置常量 ====================
# 数据集相关配置
DEFAULT_DATASET_NAME = "ceval"
SUPPORTED_DATASETS = ["ceval", "ocnli"]  # 支持的数据集列表

# 路径配置
# OpenCompass库路径
OPENCOMPASS_LIB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'OpenCompass')

# 缓存目录配置
CACHE_DIR_NAME = "cache"
DEFAULT_CACHE_DIR = "./cache"  # 相对于脚本目录的默认缓存路径

# 数据集ID配置
DATASET_IDS = {
    "ceval": "opencompass/ceval-exam",
    "ocnli": "opencompass/OCNLI-dev"
}

# 环境变量配置
ENV_COMPASS_DATA_CACHE = "COMPASS_DATA_CACHE"

# 预期数据路径配置
EXPECTED_DATA_STRUCTURE = {
    "ceval": "data/ceval/formal_ceval",
    "ocnli": "data/FewCLUE/ocnli"
}

# 错误消息配置
ERROR_MESSAGES = {
    "module_unavailable": "错误: OpenCompass模块不可用",
    "download_failed": "下载失败: {}",
    "download_may_failed": "数据集下载可能失败，请检查网络连接和权限",
    "dataset_not_supported": "数据集 {} 的下载功能尚未实现"
}

# 成功消息配置
SUCCESS_MESSAGES = {
    "download_success": "C-EVAL数据集下载成功！",
    "data_location": "数据位置: {}"
}

# 信息消息配置
INFO_MESSAGES = {
    "start_download": "开始下载C-EVAL数据集...",
    "cache_dir": "缓存目录: {}",
    "dataset_path": "数据集路径: {}"
}

# ==================== 导入模块 ====================
# 添加OpenCompass路径
sys.path.insert(0, OPENCOMPASS_LIB_PATH)

try:
    from opencompass.utils import get_data_path
    OPENCOMPASS_AVAILABLE = True
except ImportError:
    print("警告: OpenCompass模块导入失败")
    OPENCOMPASS_AVAILABLE = False


class DatasetDownloader:
    """数据集下载器"""
    
    def __init__(self):
        # 在当前脚本目录下创建cache目录
        script_dir = Path(__file__).parent
        self.cache_dir = script_dir / CACHE_DIR_NAME
        self.cache_dir.mkdir(exist_ok=True)
        print(f"缓存目录: {self.cache_dir.absolute()}")
        
    def download_ceval(self) -> bool:
        """下载C-EVAL数据集"""
        print(INFO_MESSAGES["start_download"])
        
        if not OPENCOMPASS_AVAILABLE:
            print(ERROR_MESSAGES["module_unavailable"])
            return False
        
        try:
            # 设置环境变量
            os.environ[ENV_COMPASS_DATA_CACHE] = str(self.cache_dir.absolute())
            
            # 尝试下载数据集
            print(INFO_MESSAGES["cache_dir"].format(self.cache_dir.absolute()))
            
            # 这里会触发自动下载
            data_path = get_data_path(DATASET_IDS["ceval"], local_mode=False)
            print(INFO_MESSAGES["dataset_path"].format(data_path))
            
            # 检查是否下载成功
            expected_path = self.cache_dir / EXPECTED_DATA_STRUCTURE["ceval"]
            if expected_path.exists():
                print(SUCCESS_MESSAGES["download_success"])
                print(SUCCESS_MESSAGES["data_location"].format(expected_path))
                return True
            else:
                print(ERROR_MESSAGES["download_may_failed"])
                return False
                
        except Exception as e:
            print(ERROR_MESSAGES["download_failed"].format(e))
            return False
    
    def download_dataset(self, dataset_name: str = DEFAULT_DATASET_NAME) -> bool:
        """
        下载指定的数据集
        
        Args:
            dataset_name: 数据集名称，如 'ceval', 'ocnli'
            
        Returns:
            bool: 是否下载成功
        """
        if dataset_name not in SUPPORTED_DATASETS:
            print(ERROR_MESSAGES["dataset_not_supported"].format(dataset_name))
            return False
            
        print(INFO_MESSAGES["start_download"].replace("C-EVAL", self._get_dataset_display_name(dataset_name)))
        print(INFO_MESSAGES["cache_dir"].format(self.cache_dir.absolute()))
        
        try:
            # 设置环境变量
            os.environ[ENV_COMPASS_DATA_CACHE] = str(self.cache_dir.absolute())
            
            # 获取数据集ID
            dataset_id = DATASET_IDS[dataset_name]
            print(INFO_MESSAGES["dataset_path"].format(dataset_id))
            
            # 这里会触发自动下载
            data_path = get_data_path(dataset_id, local_mode=False)
            print(INFO_MESSAGES["dataset_path"].format(data_path))
            
            # 检查是否下载成功
            expected_path = self.cache_dir / EXPECTED_DATA_STRUCTURE[dataset_name]
            if expected_path.exists():
                print(SUCCESS_MESSAGES["download_success"].replace("C-EVAL", self._get_dataset_display_name(dataset_name)))
                print(SUCCESS_MESSAGES["data_location"].format(expected_path.absolute()))
                return True
            else:
                print(ERROR_MESSAGES["download_may_failed"])
                return False
                
        except Exception as e:
            print(ERROR_MESSAGES["download_failed"].format(str(e)))
            return False
    
    def _get_dataset_display_name(self, dataset_name: str) -> str:
        """获取数据集的显示名称"""
        display_names = {
            "ceval": "C-EVAL",
            "ocnli": "FewCLUE/OCNLI"
        }
        return display_names.get(dataset_name, dataset_name)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenCompass数据集下载工具")
    parser.add_argument("--dataset", "-d", default=DEFAULT_DATASET_NAME, 
                       help=f"数据集名称 (默认: {DEFAULT_DATASET_NAME})")
    
    args = parser.parse_args()
    
    # 创建下载器
    downloader = DatasetDownloader()
    
    # 下载数据集
    success = downloader.download_dataset(args.dataset)
    
    if success:
        print(f"\n数据集 {args.dataset} 下载完成！")
        print(f"缓存目录: {downloader.cache_dir.absolute()}")
    else:
        print(f"\n数据集 {args.dataset} 下载失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
