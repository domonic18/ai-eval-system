#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集提取工具使用示例
重构版本 - 模块化架构
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
    try:
        extractor_ceval = DatasetExtractor("ceval")
        success_ceval = extractor_ceval.extract_dataset()
        
        if success_ceval:
            print(f"✅ C-EVAL数据集提取成功！")
        else:
            print(f"❌ C-EVAL数据集提取失败！")
    except Exception as e:
        print(f"❌ C-EVAL数据集提取器初始化失败: {e}")
        success_ceval = False
    
    print("\n" + "="*50 + "\n")
    
    # 示例2: 提取OCNLI数据集
    print("📚 示例2: 提取OCNLI数据集")
    try:
        extractor_ocnli = DatasetExtractor("ocnli")
        success_ocnli = extractor_ocnli.extract_dataset()
        
        if success_ocnli:
            print(f"✅ OCNLI数据集提取成功！")
        else:
            print(f"❌ OCNLI数据集提取失败！")
    except Exception as e:
        print(f"❌ OCNLI数据集提取器初始化失败: {e}")
        success_ocnli = False
    
    print("\n" + "="*50 + "\n")
    
    # 总结
    if success_ceval and success_ocnli:
        print("🎉 所有数据集提取成功！")
        print("📊 请查看 outputs/ 目录下生成的文件")
        return 0
    elif success_ceval or success_ocnli:
        print("⚠️  部分数据集提取成功，部分失败")
        print("📊 请检查失败原因并查看 outputs/ 目录下生成的文件")
        return 1
    else:
        print("❌ 所有数据集提取失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
