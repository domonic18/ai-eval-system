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

from dataset_extractor import DatasetExtractor


def main():
    """主函数示例"""
    print("=== 数据集提取工具使用示例 ===\n")

    # 示例1: 提取C-EVAL数据集
    print("📚 示例1: 提取C-EVAL数据集")
    extractor_ceval = DatasetExtractor("ceval")
    success_ceval = extractor_ceval.extract_dataset("ceval")
    
    if success_ceval:
        print(f"✅ C-EVAL数据集提取成功！")
        print(f"📁 输出目录: {extractor_ceval.output_dir.absolute()}")
    else:
        print(f"❌ C-EVAL数据集提取失败！")
    
    print("\n" + "="*50 + "\n")
    
    # 示例2: 提取OCNLI数据集
    print("📚 示例2: 提取OCNLI数据集")
    extractor_ocnli = DatasetExtractor("ocnli")
    success_ocnli = extractor_ocnli.extract_dataset("ocnli")
    
    if success_ocnli:
        print(f"✅ OCNLI数据集提取成功！")
        print(f"📁 输出目录: {extractor_ocnli.output_dir.absolute()}")
    else:
        print(f"❌ OCNLI数据集提取失败！")
    
    print("\n" + "="*50 + "\n")
    
    # 总结
    if success_ceval and success_ocnli:
        print("🎉 所有数据集提取成功！")
        print("📊 请查看生成的Excel和CSV文件")
        return 0
    else:
        print("⚠️  部分数据集提取失败，请检查数据文件是否存在")
        return 1


if __name__ == "__main__":
    sys.exit(main())
