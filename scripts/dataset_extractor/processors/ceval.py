#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C-EVAL数据集处理器
"""

import os
import csv
from typing import List, Dict, Optional
import pandas as pd
import sys

# 添加父目录到路径以导入config模块
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import (
    CSV_EXTENSION, EXCEL_EXTENSION, CSV_EXTENSION_OUT,
    ALL_SUBJECTS_FILENAME, SUBJECT_FILENAME_PREFIX,
    ALL_SUBJECTS_SHEET_NAME, SUBJECT_SHEET_NAME_PREFIX
)
from processors.base import BaseDatasetProcessor


class CEvalProcessor(BaseDatasetProcessor):
    """C-EVAL数据集处理器"""
    
    def __init__(self, dataset_name: str = "ceval"):
        super().__init__(dataset_name)
    
    def process(self, **kwargs) -> bool:
        """
        处理C-EVAL数据集
        
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
        
        # 获取所有学科
        subjects = self._get_subjects(data_path)
        if not subjects:
            print("❌ 没有找到任何学科数据")
            return False
        
        print(f"📚 找到 {len(subjects)} 个学科")
        
        # 处理每个学科
        all_data = []
        for subject in subjects:
            print(f"📖 正在处理学科: {subject}")
            subject_data = self._process_subject(data_path, subject)
            if subject_data:
                all_data.extend(subject_data)
                print(f"✅ {subject} 处理完成，共 {len(subject_data)} 条记录")
        
        if not all_data:
            print("❌ 没有处理到任何数据")
            return False
        
        print(f"📊 总共处理 {len(all_data)} 条记录")
        
        # 保存数据
        return self._save_data(all_data, subjects)
    
    def find_data_path(self) -> Optional[str]:
        """查找C-EVAL数据路径"""
        return self._find_data_path_from_config()
    
    def _get_subjects(self, data_path: str) -> List[str]:
        """获取所有学科列表"""
        subjects = []
        val_dir = os.path.join(data_path, "val")
        
        if not os.path.exists(val_dir):
            print(f"⚠️  验证集目录不存在: {val_dir}")
            return subjects
        
        for filename in os.listdir(val_dir):
            if filename.endswith("_val.csv"):
                subject = filename.replace("_val.csv", "")
                subjects.append(subject)
        
        return sorted(subjects)
    
    def _process_subject(self, data_path: str, subject: str) -> List[Dict]:
        """处理单个学科的数据"""
        subject_data = []
        val_file = os.path.join(data_path, "val", f"{subject}_val.csv")
        
        if not os.path.exists(val_file):
            print(f"⚠️  文件不存在: {val_file}")
            return subject_data
        
        try:
            with open(val_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_num, row in enumerate(reader, 1):
                    # 添加学科信息
                    row['subject'] = subject
                    subject_data.append(row)
                    
        except Exception as e:
            print(f"❌ 读取 {val_file} 时发生错误: {e}")
        
        return subject_data
    
    def _save_data(self, all_data: List[Dict], subjects: List[str]) -> bool:
        """保存所有数据"""
        try:
            # 保存所有学科汇总数据
            excel_filename = f"{ALL_SUBJECTS_FILENAME}{EXCEL_EXTENSION}"
            self.save_to_excel(all_data, excel_filename, ALL_SUBJECTS_SHEET_NAME)
            
            csv_filename = f"{ALL_SUBJECTS_FILENAME}{CSV_EXTENSION_OUT}"
            self.save_to_csv(all_data, csv_filename)
            
            # 保存各学科单独数据
            for subject in subjects:
                subject_data = [item for item in all_data if item.get('subject') == subject]
                if subject_data:
                    excel_filename = f"{SUBJECT_FILENAME_PREFIX.format(subject)}{EXCEL_EXTENSION}"
                    sheet_name = SUBJECT_SHEET_NAME_PREFIX.format(subject)
                    self.save_to_csv(subject_data, csv_filename)
            
            # 输出统计信息
            print(f"\n📈 数据统计:")
            print(f"   总记录数: {len(all_data)}")
            print(f"   学科数量: {len(subjects)}")
            print(f"   各学科记录数:")
            for subject in subjects:
                count = len([item for item in all_data if item.get('subject') == subject])
                print(f"     {subject}: {count} 条")
            
            return True
            
        except Exception as e:
            print(f"❌ 保存数据时发生错误: {e}")
            return False
