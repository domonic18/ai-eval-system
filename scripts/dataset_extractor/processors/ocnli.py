#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCNLI数据集处理器
"""

import os
import json
from typing import List, Dict, Optional
import pandas as pd
import sys

# 添加父目录到路径以导入config模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import EXCEL_EXTENSION, CSV_EXTENSION_OUT
from processors.base import BaseDatasetProcessor


class OCNLIProcessor(BaseDatasetProcessor):
    """OCNLI数据集处理器"""
    
    def __init__(self, dataset_name: str = "ocnli"):
        super().__init__(dataset_name)
    
    def process(self, **kwargs) -> bool:
        """
        处理OCNLI数据集
        
        Returns:
            bool: 是否成功
        """
        print(f"🔄 开始提取 {self.config['name']} 数据集...")
        
        # 查找数据路径
        data_path = self.find_data_path()
        if not data_path:
            print(f"❌ 找不到 {self.config['name']} 数据目录")
            return False
        
        print(f"📂 找到数据目录: {data_path}")
        
        # 读取数据文件
        data_files = self._get_data_files(data_path)
        if not data_files:
            print(f"❌ 在 {data_path} 中找不到数据文件")
            return False
        
        # 处理数据
        all_data = self._process_data_files(data_files)
        if not all_data:
            print("❌ 没有读取到任何数据")
            return False
        
        print(f"📊 总共读取到 {len(all_data)} 条记录")
        
        # 保存数据
        return self._save_data(all_data)
    
    def find_data_path(self) -> Optional[str]:
        """查找OCNLI数据路径"""
        return self._find_data_path_from_config()
    
    def _get_data_files(self, data_path: str) -> List[tuple]:
        """获取数据文件列表"""
        data_files = []
        for split in ['dev_few_all', 'test_public']:
            file_path = os.path.join(data_path, f"{split}.json")
            if os.path.exists(file_path):
                data_files.append((split, file_path))
        
        return data_files
    
    def _process_data_files(self, data_files: List[tuple]) -> List[Dict]:
        """处理所有数据文件"""
        all_data = []
        
        for split_name, file_path in data_files:
            print(f"📖 正在读取 {split_name} 数据...")
            
            try:
                split_data = self._read_json_file(file_path, split_name)
                if split_data:
                    all_data.extend(split_data)
                    print(f"✅ {split_name} 数据读取完成，共 {len(split_data)} 条记录")
                    
            except Exception as e:
                print(f"❌ 读取 {file_path} 时发生错误: {e}")
                continue
        
        return all_data
    
    def _read_json_file(self, file_path: str, split_name: str) -> List[Dict]:
        """读取JSON文件"""
        split_data = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    item = json.loads(line.strip())
                    # 添加分割信息
                    item['split'] = split_name
                    split_data.append(item)
                except json.JSONDecodeError as e:
                    print(f"⚠️  第 {line_num} 行JSON解析错误: {e}")
                    continue
        
        return split_data
    
    def _save_data(self, data: List[Dict]) -> bool:
        """保存OCNLI数据"""
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
