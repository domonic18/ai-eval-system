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

# 支持的数据集列表
SUPPORTED_DATASETS = {
    "ceval": {
        "name": "C-EVAL",
        "type": "CEvalDataset",
        "paths": [
            "./cache/data/ceval/formal_ceval",
            "../workspace/opencompass/data/ceval/formal_ceval",
            "../../workspace/opencompass/data/ceval/formal_ceval",
            "~/.cache/opencompass/data/ceval/formal_ceval"
        ],
        "file_extension": "_val.csv",
        "fields": ['explanation', 'answer'],
        "subject_field": 'subject'
    },
    "ocnli": {
        "name": "FewCLUE/OCNLI",
        "type": "CMNLIDatasetV2", 
        "paths": [
            "./cache/data/FewCLUE/ocnli",
            "../workspace/opencompass/data/FewCLUE/ocnli",
            "../../workspace/opencompass/data/FewCLUE/ocnli",
            "~/.cache/opencompass/data/FewCLUE/ocnli"
        ],
        "file_extension": ".json",
        "fields": ['sentence1', 'sentence2', 'label'],
        "subject_field": None
    }
}

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
    
    def __init__(self, dataset_name: str):
        """
        初始化数据集提取器
        
        Args:
            dataset_name: 数据集名称，如 'ceval', 'ocnli'
        """
        self.dataset_name = dataset_name
        
        # 验证数据集是否支持
        if dataset_name not in SUPPORTED_DATASETS:
            raise ValueError(f"不支持的数据集: {dataset_name}。支持的数据集: {list(SUPPORTED_DATASETS.keys())}")
        
        # 获取数据集配置
        self.dataset_config = SUPPORTED_DATASETS[dataset_name]
        self.dataset_type = self.dataset_config["type"]
        self.dataset_paths = self.dataset_config["paths"]
        self.file_extension = self.dataset_config["file_extension"]
        self.fields = self.dataset_config["fields"]
        self.subject_field = self.dataset_config["subject_field"]
        
        # 设置输出目录
        self.output_dir = Path(f"./{dataset_name}")
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"✅ 初始化 {self.dataset_config['name']} 数据集提取器")
        print(f"📁 输出目录: {self.output_dir.absolute()}")
        
    def extract_dataset(self, dataset_name: str, **kwargs) -> bool:
        """
        提取数据集
        
        Args:
            dataset_name: 数据集名称
            **kwargs: 其他参数
            
        Returns:
            bool: 是否成功
        """
        try:
            # 根据数据集类型调用相应的提取逻辑
            if dataset_name == "ceval":
                return self._extract_ceval_dataset(**kwargs)
            elif dataset_name == "ocnli":
                return self._extract_ocnli_dataset(**kwargs)
            else:
                print(f"❌ 不支持的数据集类型: {dataset_name}")
                return False
        except Exception as e:
            print(f"❌ 提取数据集时发生错误: {e}")
            return False
    
    def save_to_excel(self, data: List[Dict], filename: str, sheet_name: str = "Sheet1"):
        """保存数据到Excel文件"""
        try:
            df = pd.DataFrame(data)
            filepath = self.output_dir / filename
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"✅ Excel文件保存成功: {filepath}")
            
        except Exception as e:
            print(f"❌ 保存Excel文件失败: {e}")
    
    def save_to_csv(self, data: List[Dict], filename: str):
        """保存数据到CSV文件"""
        try:
            df = pd.DataFrame(data)
            filepath = self.output_dir / filename
            
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"✅ CSV文件保存成功: {filepath}")
            
        except Exception as e:
            print(f"❌ 保存CSV文件失败: {e}")
    
    def _find_data_path(self) -> Optional[str]:
        """
        查找数据集的根目录路径
        
        Returns:
            str: 找到的根目录路径，如果未找到则返回None
        """
        for path in self.dataset_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path
        return None
    
    def _extract_ceval_dataset(self, **kwargs) -> bool:
        """提取C-EVAL数据集的基础方法"""
        print(f"🔄 开始提取 {self.dataset_config['name']} 数据集...")
        # 这里可以添加C-EVAL的通用提取逻辑
        return False
    
    def _extract_ocnli_dataset(self, **kwargs) -> bool:
        """
        提取OCNLI数据集
        
        Returns:
            bool: 是否成功
        """
        print(f"\n🔄 开始提取 {self.dataset_config['name']} 数据集...")
        
        # 查找数据文件
        data_path = self._find_data_path()
        if not data_path:
            print(f"❌ 找不到 {self.dataset_config['name']} 数据目录")
            return False
        
        print(f"📂 找到数据目录: {data_path}")
        
        # 读取数据文件
        data_files = []
        for split in ['dev_few_all', 'test_public']:
            file_path = os.path.join(data_path, f"{split}.json")
            if os.path.exists(file_path):
                data_files.append((split, file_path))
        
        if not data_files:
            print(f"❌ 在 {data_path} 中找不到数据文件")
            return False
        
        all_data = []
        
        # 处理每个数据文件
        for split_name, file_path in data_files:
            print(f"📖 正在读取 {split_name} 数据...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    split_data = []
                    for line_num, line in enumerate(f, 1):
                        try:
                            item = json.loads(line.strip())
                            # 添加分割信息
                            item['split'] = split_name
                            split_data.append(item)
                        except json.JSONDecodeError as e:
                            print(f"⚠️  第 {line_num} 行JSON解析错误: {e}")
                            continue
                    
                    print(f"✅ {split_name} 数据读取完成，共 {len(split_data)} 条记录")
                    all_data.extend(split_data)
                    
            except Exception as e:
                print(f"❌ 读取 {file_path} 时发生错误: {e}")
                continue
        
        if not all_data:
            print("❌ 没有读取到任何数据")
            return False
        
        print(f"📊 总共读取到 {len(all_data)} 条记录")
        
        # 保存数据
        return self._save_ocnli_data(all_data)
    
    def _save_ocnli_data(self, data: List[Dict]) -> bool:
        """
        保存OCNLI数据
        
        Args:
            data: 数据列表
            
        Returns:
            bool: 是否成功
        """
        try:
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 重新排列列顺序
            columns = ['split', 'sentence1', 'sentence2', 'label']
            # 添加其他可能存在的列
            for col in df.columns:
                if col not in columns:
                    columns.append(col)
            
            df = df[columns]
            
            # 保存为Excel
            excel_filename = f"ocnli_data{EXCEL_EXTENSION}"
            excel_path = self.output_dir / excel_filename
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 所有数据工作表
                df.to_excel(writer, sheet_name='OCNLI_All_Data', index=False)
                
                # 按分割分组的工作表
                for split in df['split'].unique():
                    split_df = df[df['split'] == split]
                    sheet_name = f'OCNLI_{split.replace("_", " ").title()}'
                    # Excel工作表名称限制为31个字符
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]
                    split_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"✅ Excel文件保存成功: {excel_path}")
            
            # 保存为CSV
            csv_filename = f"ocnli_data{CSV_EXTENSION_OUT}"
            csv_path = self.output_dir / csv_filename
            df.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"✅ CSV文件保存成功: {csv_path}")
            
            # 输出统计信息
            print(f"\n📈 数据统计:")
            print(f"   总记录数: {len(data)}")
            print(f"   分割分布:")
            for split in df['split'].unique():
                count = len(df[df['split'] == split])
                print(f"     {split}: {count} 条")
            
            print(f"   标签分布:")
            for label in df['label'].unique():
                count = len(df[df['label'] == label])
                print(f"     {label}: {count} 条")
            
            return True
            
        except Exception as e:
            print(f"❌ 保存数据时发生错误: {e}")
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
