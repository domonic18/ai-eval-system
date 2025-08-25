#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集提取工具使用示例
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from dataset_extractor import CEvalExtractor


def main():
    """主函数示例"""
    print("=== C-EVAL数据集提取示例 ===\n")
    
    # 创建提取器
    extractor = CEvalExtractor("ceval")
    
    # 提取数据集
    success = extractor.extract_dataset("ceval")
    
    if success:
        print(f"\n✅ 数据集提取成功！")
        print(f"📁 输出目录: {extractor.output_dir.absolute()}")
        print(f"📊 请查看生成的Excel和CSV文件")
    else:
        print(f"\n❌ 数据集提取失败！")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
