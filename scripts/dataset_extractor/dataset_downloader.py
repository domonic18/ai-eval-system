#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集下载工具主模块
重构版本 - 模块化架构
"""

import sys
from pathlib import Path

from config import get_supported_datasets, get_dataset_config


class DatasetDownloader:
    """数据集下载器主类"""
    
    def __init__(self):
        """初始化下载器"""
        self.downloaders = {}
        self._init_downloaders()
    
    def _init_downloaders(self):
        """初始化各种下载器"""
        try:
            from downloaders.opencompass import OpenCompassDownloader
            self.downloaders['opencompass'] = OpenCompassDownloader()
        except ImportError as e:
            print(f"⚠️  OpenCompass下载器初始化失败: {e}")
    
    def _get_dataset_config(self, dataset_name: str) -> dict:
        """获取数据集配置"""
        from config import SUPPORTED_DATASETS
        if dataset_name not in SUPPORTED_DATASETS:
            raise ValueError(f"不支持的数据集: {dataset_name}")
        return SUPPORTED_DATASETS[dataset_name]
    
    def download_dataset(self, dataset_name: str) -> bool:
        """
        下载指定数据集
        
        Args:
            dataset_name: 数据集名称
            
        Returns:
            bool: 是否下载成功
        """
        dataset_config = self._get_dataset_config(dataset_name)
        print(f"🔄 开始下载 {dataset_config['name']} 数据集...")
        
        # 根据数据集类型选择下载器
        if dataset_name in ["ceval", "ocnli"]:
            # 使用OpenCompass下载器
            if 'opencompass' in self.downloaders:
                return self.downloaders['opencompass'].download_dataset(dataset_name)
            else:
                print("❌ OpenCompass下载器不可用")
                return False
        else:
            print(f"❌ 没有可用的下载器支持 {dataset_name}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据集下载工具")
    parser.add_argument("dataset", choices=get_supported_datasets(), help="要下载的数据集名称")
    
    args = parser.parse_args()
    
    try:
        downloader = DatasetDownloader()
        success = downloader.download_dataset(args.dataset)
        
        if success:
            print(f"\n🎉 {args.dataset} 数据集下载成功！")
            return 0
        else:
            print(f"\n❌ {args.dataset} 数据集下载失败！")
            return 1
            
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
