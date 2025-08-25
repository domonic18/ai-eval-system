#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集读取和导出脚本
支持OpenCompass中的各种数据集，特别是C-EVAL数据集
"""

import os
import sys
import csv
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# ==================== 配置常量 ====================
# 数据集相关配置
DEFAULT_DATASET_NAME = "ceval"
DEFAULT_OUTPUT_FORMAT = "both"  # excel, csv, both

# 路径配置
# OpenCompass库路径
OPENCOMPASS_LIB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'libs', 'OpenCompass')

# 数据路径配置 - 按优先级排序
CEVAL_DATA_PATHS = [
    "./cache/data/ceval/formal_ceval",                    # 当前脚本目录下的cache
    "../workspace/opencompass/data/ceval/formal_ceval",   # 上级workspace目录
    "../../workspace/opencompass/data/ceval/formal_ceval", # 上上级workspace目录
    "~/.cache/opencompass/data/ceval/formal_ceval"        # 用户缓存目录
]

# 环境变量配置
ENV_DATASET_SOURCE = "Local"
ENV_COMPASS_DATA_CACHE = "./cache"

# 文件扩展名配置
CSV_EXTENSION = "_val.csv"
EXCEL_EXTENSION = ".xlsx"
CSV_EXTENSION_OUT = ".csv"

# 数据分割配置
DEFAULT_SPLIT = "val"
TRAIN_SPLIT = "dev"
TEST_SPLIT = "test"

# 输出文件命名配置
ALL_SUBJECTS_FILENAME = "ceval_all_subjects_data"
SUBJECT_FILENAME_PREFIX = "ceval_{}_data"

# Excel工作表名称配置
ALL_SUBJECTS_SHEET_NAME = "C-EVAL_All_Subjects"
SUBJECT_SHEET_NAME_PREFIX = "C-EVAL_{}"

# 数据字段配置
DEFAULT_FIELDS = ['explanation', 'answer']
SUBJECT_FIELD_NAME = 'subject'

# ==================== 导入模块 ====================
# 添加OpenCompass路径
sys.path.insert(0, OPENCOMPASS_LIB_PATH)

try:
    from opencompass.utils import get_data_path
    from opencompass.datasets.ceval import CEvalDataset
    OPENCOMPASS_AVAILABLE = True
except ImportError:
    print("警告: OpenCompass模块导入失败，将使用基础CSV读取功能")
    OPENCOMPASS_AVAILABLE = False


class DatasetExtractor:
    """数据集提取器基类"""
    
    def __init__(self, dataset_name: str = DEFAULT_DATASET_NAME):
        # 在当前脚本目录下创建数据集名称目录
        script_dir = Path(__file__).parent
        self.output_dir = script_dir / dataset_name
        self.output_dir.mkdir(exist_ok=True)
        print(f"输出目录: {self.output_dir.absolute()}")
        
    def extract_dataset(self, dataset_name: str, **kwargs) -> bool:
        """提取数据集的主要方法"""
        raise NotImplementedError("子类必须实现此方法")
    
    def save_to_excel(self, data: List[Dict], filename: str, sheet_name: str = "Sheet1"):
        """保存数据到Excel文件"""
        if not data:
            print(f"警告: 没有数据可保存到 {filename}")
            return False
            
        df = pd.DataFrame(data)
        output_path = self.output_dir / filename
        
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"数据已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存Excel文件失败: {e}")
            return False
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """保存数据到CSV文件"""
        if not data:
            print(f"警告: 没有数据可保存到 {filename}")
            return False
            
        output_path = self.output_dir / filename
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
            print(f"数据已保存到: {output_path}")
            return True
        except Exception as e:
            print(f"保存CSV文件失败: {e}")
            return False


class CEvalExtractor(DatasetExtractor):
    """C-EVAL数据集提取器"""
    
    def __init__(self, dataset_name: str = DEFAULT_DATASET_NAME):
        super().__init__(dataset_name)
        self.dataset_path = None
        
    def extract_dataset(self, dataset_name: str = DEFAULT_DATASET_NAME, **kwargs) -> bool:
        """提取C-EVAL数据集"""
        print(f"开始提取C-EVAL数据集: {dataset_name}")
        
        # 尝试获取数据集路径
        if OPENCOMPASS_AVAILABLE:
            try:
                # 设置环境变量以使用本地模式
                os.environ['DATASET_SOURCE'] = ENV_DATASET_SOURCE
                os.environ['COMPASS_DATA_CACHE'] = ENV_COMPASS_DATA_CACHE
                
                # 获取数据路径
                self.dataset_path = get_data_path("opencompass/ceval-exam", local_mode=True)
                print(f"数据集路径: {self.dataset_path}")
                
                # 使用OpenCompass的CEvalDataset加载数据
                return self._extract_with_opencompass(dataset_name)
                
            except Exception as e:
                print(f"使用OpenCompass加载失败: {e}")
                print("尝试直接读取CSV文件...")
        
        # 回退到直接CSV读取
        return self._extract_from_csv(dataset_name)
    
    def _extract_with_opencompass(self, dataset_name: str) -> bool:
        """使用OpenCompass加载数据集"""
        try:
            # 加载数据集
            dataset = CEvalDataset.load(self.dataset_path, dataset_name)
            
            if DEFAULT_SPLIT not in dataset:
                print(f"警告: {DEFAULT_SPLIT}集不存在")
                return False
            
            val_data = dataset[DEFAULT_SPLIT]
            print(f"成功加载{DEFAULT_SPLIT}集，共 {len(val_data)} 条数据")
            
            # 转换为列表格式
            data_list = []
            for i in range(len(val_data)):
                item = val_data[i]
                data_list.append({
                    'id': i,
                    'question': item.get('question', ''),
                    'A': item.get('A', ''),
                    'B': item.get('B', ''),
                    'C': item.get('C', ''),
                    'D': item.get('D', ''),
                    'answer': item.get('answer', ''),
                    'explanation': item.get('explanation', ''),
                    'subject': dataset_name
                })
            
            # 保存到Excel
            excel_filename = f"{SUBJECT_FILENAME_PREFIX.format(dataset_name)}{EXCEL_EXTENSION}"
            self.save_to_excel(data_list, excel_filename, f"{SUBJECT_SHEET_NAME_PREFIX.format(dataset_name)}")
            
            # 保存到CSV
            csv_filename = f"{SUBJECT_FILENAME_PREFIX.format(dataset_name)}{CSV_EXTENSION_OUT}"
            self.save_to_csv(data_list, csv_filename)
            
            return True
            
        except Exception as e:
            print(f"OpenCompass数据加载失败: {e}")
            return False
    
    def _extract_from_csv(self, dataset_name: str) -> bool:
        """直接从CSV文件读取数据"""
        # 尝试多个可能的路径
        data_path = None
        for path in CEVAL_DATA_PATHS:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                data_path = expanded_path
                break
        
        if not data_path:
            print("错误: 找不到C-EVAL数据目录")
            return False
        
        print(f"使用数据路径: {data_path}")
        
        # 读取所有科目的数据
        all_data = []
        subjects = []
        
        # 获取所有科目
        val_dir = os.path.join(data_path, DEFAULT_SPLIT)
        if os.path.exists(val_dir):
            for filename in os.listdir(val_dir):
                if filename.endswith(CSV_EXTENSION):
                    subject = filename.replace(CSV_EXTENSION, '')
                    subjects.append(subject)
        
        print(f"找到 {len(subjects)} 个科目")
        
        # 读取每个科目的数据
        for subject in subjects:
            csv_file = os.path.join(val_dir, f"{subject}{CSV_EXTENSION}")
            if os.path.exists(csv_file):
                try:
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            row[SUBJECT_FIELD_NAME] = subject
                            all_data.append(row)
                    print(f"已读取科目 {subject}: {len([d for d in all_data if d[SUBJECT_FIELD_NAME] == subject])} 条数据")
                except Exception as e:
                    print(f"读取科目 {subject} 失败: {e}")
        
        if not all_data:
            print("错误: 没有读取到任何数据")
            return False
        
        print(f"总共读取到 {len(all_data)} 条数据")
        
        # 保存到Excel
        excel_filename = f"{ALL_SUBJECTS_FILENAME}{EXCEL_EXTENSION}"
        self.save_to_excel(all_data, excel_filename, ALL_SUBJECTS_SHEET_NAME)
        
        # 保存到CSV
        csv_filename = f"{ALL_SUBJECTS_FILENAME}{CSV_EXTENSION_OUT}"
        self.save_to_csv(all_data, csv_filename)
        
        # 按科目分别保存
        for subject in subjects:
            subject_data = [d for d in all_data if d[SUBJECT_FIELD_NAME] == subject]
            if subject_data:
                subject_excel = f"{SUBJECT_FILENAME_PREFIX.format(subject)}{EXCEL_EXTENSION}"
                self.save_to_excel(subject_data, subject_excel, f"{SUBJECT_SHEET_NAME_PREFIX.format(subject)}")
                
                subject_csv = f"{SUBJECT_FILENAME_PREFIX.format(subject)}{CSV_EXTENSION_OUT}"
                self.save_to_csv(subject_data, subject_csv)
        
        return True


class GenericDatasetExtractor(DatasetExtractor):
    """通用数据集提取器"""
    
    def __init__(self, dataset_name: str = DEFAULT_DATASET_NAME):
        super().__init__(dataset_name)
    
    def extract_dataset(self, dataset_name: str, **kwargs) -> bool:
        """提取通用数据集"""
        print(f"开始提取数据集: {dataset_name}")
        
        # 这里可以添加对其他数据集的支持
        # 例如：MMLU、AGIEval等
        
        print(f"数据集 {dataset_name} 的提取功能尚未实现")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="OpenCompass数据集提取工具")
    parser.add_argument("--dataset", "-d", default=DEFAULT_DATASET_NAME, 
                       help=f"数据集名称 (默认: {DEFAULT_DATASET_NAME})")
    parser.add_argument("--format", "-f", choices=["excel", "csv", "both"], 
                       default=DEFAULT_OUTPUT_FORMAT, help=f"输出格式 (默认: {DEFAULT_OUTPUT_FORMAT})")
    
    args = parser.parse_args()
    
    # 根据数据集类型选择提取器
    if args.dataset.lower() == DEFAULT_DATASET_NAME:
        extractor = CEvalExtractor(args.dataset)
    else:
        extractor = GenericDatasetExtractor(args.dataset)
    
    # 提取数据集
    success = extractor.extract_dataset(args.dataset)
    
    if success:
        print(f"\n数据集 {args.dataset} 提取完成！")
        print(f"输出目录: {extractor.output_dir.absolute()}")
    else:
        print(f"\n数据集 {args.dataset} 提取失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
