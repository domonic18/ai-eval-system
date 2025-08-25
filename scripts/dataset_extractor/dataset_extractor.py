#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集提取工具主模块
重构版本 - 模块化架构
"""

import sys
from pathlib import Path
from typing import Optional

# 添加OpenCompass库路径
from config import OPENCOMPASS_LIB_PATH, get_supported_datasets, get_dataset_config

# 尝试导入OpenCompass模块
try:
    sys.path.insert(0, str(OPENCOMPASS_LIB_PATH))
    from opencompass.datasets import CEvalDataset
    from opencompass.utils import get_data_path
    OPENCOMPASS_AVAILABLE = True
except ImportError:
    OPENCOMPASS_AVAILABLE = False
    print("警告: OpenCompass模块导入失败，将使用基础功能")


class DatasetExtractor:
    """数据集提取器主类"""
    
    def __init__(self, dataset_name: str):
        """
        初始化数据集提取器
        
        Args:
            dataset_name: 数据集名称
        """
        self.dataset_name = dataset_name
        
        # 验证数据集是否支持
        if dataset_name not in get_supported_datasets():
            raise ValueError(f"不支持的数据集: {dataset_name}。支持的数据集: {get_supported_datasets()}")
        
        # 获取数据集配置
        self.config = get_dataset_config(dataset_name)
        
        print(f"✅ 初始化 {self.config['name']} 数据集提取器")
    
    def extract_dataset(self, **kwargs) -> bool:
        """
        提取数据集
        
        Returns:
            bool: 是否成功
        """
        try:
            # 根据数据集类型调用相应的处理器
            if self.dataset_name == "ceval":
                from processors.ceval import CEvalProcessor
                processor = CEvalProcessor(self.dataset_name)
                return processor.process(**kwargs)
            elif self.dataset_name == "ocnli":
                from processors.ocnli import OCNLIProcessor
                processor = OCNLIProcessor(self.dataset_name)
                return processor.process(**kwargs)
            elif self.dataset_name == "truthfulqa":
                from processors.truthfulqa import TruthfulQAProcessor
                processor = TruthfulQAProcessor(self.dataset_name)
                return processor.process(**kwargs)
            else:
                print(f"❌ 不支持的数据集类型: {self.dataset_name}")
                return False
                
        except Exception as e:
            print(f"❌ 提取数据集时发生错误: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="数据集提取工具")
    parser.add_argument("dataset", choices=get_supported_datasets(), help="要提取的数据集名称")
    parser.add_argument("--format", choices=["excel", "csv", "both"], default="both", help="输出格式")
    
    args = parser.parse_args()
    
    try:
        extractor = DatasetExtractor(args.dataset)
        success = extractor.extract_dataset(format=args.format)
        
        if success:
            print(f"\n🎉 {args.dataset} 数据集提取成功！")
            return 0
        else:
            print(f"\n❌ {args.dataset} 数据集提取失败！")
            return 1
            
    except Exception as e:
        print(f"❌ 程序执行错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
