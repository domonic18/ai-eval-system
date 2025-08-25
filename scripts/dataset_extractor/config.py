#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据集提取工具配置管理模块
"""

import os
from pathlib import Path

# ==================== 基础配置 ====================
# 脚本根目录
SCRIPT_ROOT = Path(__file__).parent

# 输出目录配置
OUTPUT_BASE_DIR = SCRIPT_ROOT / "outputs"
OUTPUT_BASE_DIR.mkdir(exist_ok=True)

# 缓存目录配置
CACHE_BASE_DIR = SCRIPT_ROOT / "cache"
CACHE_BASE_DIR.mkdir(exist_ok=True)

# OpenCompass库路径
OPENCOMPASS_LIB_PATH = SCRIPT_ROOT.parent.parent / "libs" / "OpenCompass"

# ==================== 数据集配置 ====================
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
        "subject_field": 'subject',
        "output_dir": "ceval"
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
        "subject_field": None,
        "output_dir": "ocnli"
    }
}

# ==================== 数据集下载配置 ====================
DATASET_IDS = {
    "ceval": "opencompass/ceval-exam",
    "ocnli": "opencompass/OCNLI-dev"
}

EXPECTED_DATA_STRUCTURE = {
    "ceval": "data/ceval/formal_ceval",
    "ocnli": "data/FewCLUE/ocnli"
}

# ==================== 环境变量配置 ====================
ENV_DATASET_SOURCE = "Local"
ENV_COMPASS_DATA_CACHE = "COMPASS_DATA_CACHE"

# ==================== 文件格式配置 ====================
CSV_EXTENSION = "_val.csv"
EXCEL_EXTENSION = ".xlsx"
CSV_EXTENSION_OUT = ".csv"

# ==================== 数据分割配置 ====================
DEFAULT_SPLIT = "val"
TRAIN_SPLIT = "dev"
TEST_SPLIT = "test"

# ==================== 输出文件命名配置 ====================
ALL_SUBJECTS_FILENAME = "ceval_all_subjects_data"
SUBJECT_FILENAME_PREFIX = "ceval_{}_data"

# Excel工作表名称配置
ALL_SUBJECTS_SHEET_NAME = "C-EVAL_All_Subjects"
SUBJECT_SHEET_NAME_PREFIX = "C-EVAL_{}"

# ==================== 消息配置 ====================
ERROR_MESSAGES = {
    "module_unavailable": "错误: OpenCompass模块不可用",
    "download_failed": "下载失败: {}",
    "download_may_failed": "数据集下载可能失败，请检查网络连接和权限",
    "dataset_not_supported": "数据集 {} 的下载功能尚未实现"
}

SUCCESS_MESSAGES = {
    "download_success": "{}数据集下载成功！",
    "data_location": "数据位置: {}"
}

INFO_MESSAGES = {
    "start_download": "开始下载{}数据集...",
    "cache_dir": "缓存目录: {}",
    "dataset_path": "数据集路径: {}"
}

# ==================== 工具函数 ====================
def get_output_dir(dataset_name: str) -> Path:
    """获取指定数据集的输出目录"""
    if dataset_name not in SUPPORTED_DATASETS:
        raise ValueError(f"不支持的数据集: {dataset_name}")
    
    output_dir = OUTPUT_BASE_DIR / SUPPORTED_DATASETS[dataset_name]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

def get_cache_dir() -> Path:
    """获取缓存目录"""
    return CACHE_BASE_DIR

def get_dataset_config(dataset_name: str) -> dict:
    """获取指定数据集的配置"""
    if dataset_name not in SUPPORTED_DATASETS:
        raise ValueError(f"不支持的数据集: {dataset_name}")
    
    return SUPPORTED_DATASETS[dataset_name]

def get_supported_datasets() -> list:
    """获取支持的数据集列表"""
    return list(SUPPORTED_DATASETS.keys())
