# 数据集提取工具

这是一个用于从OpenCompass评测系统中提取数据集信息的工具，采用模块化架构设计，支持多种数据集类型。

## 🎯 支持的数据集

### 1. C-EVAL 数据集
- **描述**: 中文语言模型评测数据集，包含52个学科领域的考试题目
- **数据类型**: 选择题（A、B、C、D四个选项）
- **数据格式**: CSV文件，包含问题、选项、答案、解释等字段
- **输出内容**: 所有学科数据汇总 + 各学科单独数据

### 2. FewCLUE/OCNLI 数据集
- **描述**: 中文自然语言推理数据集，用于测试模型的语言理解能力
- **数据类型**: 句子对分类任务
- **数据格式**: JSON文件，包含句子对和标签
- **数据字段**: 
  - `sentence1`: 第一个句子
  - `sentence2`: 第二个句子
  - `label`: 标签（A: 蕴含, B: 矛盾, C: 中性）
- **输出内容**: 所有数据汇总 + 按分割分组的数据

## 🏗️ 架构设计

### 模块化结构
```
scripts/dataset_extractor/
├── config.py                    # 配置管理模块
├── dataset_extractor.py         # 主提取器
├── dataset_downloader.py        # 主下载器
├── processors/                  # 数据集处理器包
│   ├── __init__.py
│   ├── base.py                 # 基础处理器抽象类
│   ├── ceval.py                # C-EVAL处理器
│   └── ocnli.py                # OCNLI处理器
├── downloaders/                 # 数据集下载器包
│   ├── __init__.py
│   ├── base.py                 # 基础下载器抽象类
│   └── opencompass.py          # OpenCompass下载器
├── outputs/                     # 输出目录（自动创建）
│   ├── ceval/                  # C-EVAL输出
│   └── ocnli/                  # OCNLI输出
├── cache/                       # 缓存目录（自动创建）
├── run_example.py               # 使用示例
├── requirements.txt             # 依赖包
└── .gitignore                   # Git忽略文件
```

### 设计原则
- **高内聚**: 每个模块职责单一，功能完整
- **低耦合**: 模块间通过抽象接口交互
- **易扩展**: 新增数据集只需实现相应的处理器和下载器
- **配置集中**: 所有配置信息统一管理

## 🚀 使用方法

### 1. 下载数据集

```bash
# 下载C-EVAL数据集
python dataset_downloader.py ceval

# 下载OCNLI数据集
python dataset_downloader.py ocnli
```

### 2. 提取数据集

```bash
# 提取C-EVAL数据集
python dataset_extractor.py ceval

# 提取OCNLI数据集
python dataset_extractor.py ocnli
```

### 3. 使用Python API

```python
from dataset_extractor import DatasetExtractor

# 提取C-EVAL数据集
extractor = DatasetExtractor("ceval")
success = extractor.extract_dataset()

# 提取OCNLI数据集
extractor = DatasetExtractor("ocnli")
success = extractor.extract_dataset()
```

## 📁 输出结构

### 输出目录
所有输出文件都保存在 `outputs/` 目录下，按数据集名称分类：

```
outputs/
├── ceval/                       # C-EVAL数据集输出
│   ├── ceval_all_subjects_data.xlsx
│   ├── ceval_all_subjects_data.csv
│   ├── ceval_math_data.xlsx
│   ├── ceval_math_data.csv
│   └── ...
└── ocnli/                       # OCNLI数据集输出
    ├── ocnli_data.xlsx
    └── ocnli_data.csv
```

### 缓存目录
下载的数据集保存在 `cache/` 目录下：

```
cache/
├── data/
│   ├── ceval/formal_ceval/     # C-EVAL数据
│   └── FewCLUE/ocnli/          # OCNLI数据
```

## 🔧 扩展新数据集

### 1. 添加数据集配置
在 `config.py` 中的 `SUPPORTED_DATASETS` 添加新数据集配置。

### 2. 实现数据处理器
继承 `BaseDatasetProcessor` 类，实现 `process()` 和 `find_data_path()` 方法。

### 3. 实现数据下载器（可选）
继承 `BaseDatasetDownloader` 类，实现 `download_dataset()` 方法。

### 示例：添加新数据集
```python
# 1. 在config.py中添加配置
"new_dataset": {
    "name": "New Dataset",
    "type": "NewDatasetType",
    "paths": ["path1", "path2"],
    "file_extension": ".json",
    "fields": ["field1", "field2"],
    "subject_field": None,
    "output_dir": "new_dataset"
}

# 2. 创建处理器
class NewDatasetProcessor(BaseDatasetProcessor):
    def process(self, **kwargs) -> bool:
        # 实现数据处理逻辑
        pass
    
    def find_data_path(self) -> Optional[str]:
        # 实现数据路径查找
        pass
```

## 📋 依赖要求

```bash
pip install -r requirements.txt
```

主要依赖：
- `pandas>=1.3.0`: 数据处理
- `openpyxl>=3.0.0`: Excel文件支持
- `pathlib2>=2.3.0`: 路径处理

## 🐛 故障排除

### 常见问题
1. **找不到数据目录**: 检查配置文件中的路径设置
2. **模块导入失败**: 确保OpenCompass库路径正确
3. **权限问题**: 确保有写入输出和缓存目录的权限

### 调试建议
- 检查配置文件中的路径设置
- 验证数据文件是否存在
- 查看详细的错误日志

## 📝 更新日志

### v2.0.0 (重构版本)
- 🏗️ 重构为模块化架构
- 📁 统一输出到 `outputs/` 目录
- 🔧 支持多种数据集类型
- 📊 改进的配置管理
- 🚀 更好的扩展性

### v1.0.0 (初始版本)
- ✅ 支持C-EVAL数据集
- ✅ 支持OCNLI数据集
- ✅ Excel和CSV输出格式
