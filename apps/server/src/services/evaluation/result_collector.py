from pathlib import Path
import zipfile
import json
import os
from typing import Dict, List
from models.eval import Evaluation
from core.database import SessionLocal
import re

class ResultCollector:
    def __init__(self, eval_id: int, work_dir: Path):
        """
        Args:
            eval_id: 评估任务ID
            work_dir: OpenCompass输出目录（eval_{eval_id}）
        """
        self.eval_id = eval_id
        self.base_dir = work_dir / "logs" / f"eval_{eval_id}"  # 使用Path运算符
        self.timestamp_dir = self._find_latest_timestamp_dir()
        self.results_dir = self.timestamp_dir / "results"
        self.summary_dir = self.timestamp_dir / "summary"
        self.predictions_dir = self.timestamp_dir / "predictions"
        
    def _find_latest_timestamp_dir(self) -> Path:
        """安全查找最新时间戳目录"""
        if not self.base_dir.exists():
            raise FileNotFoundError(f"基础目录不存在: {self.base_dir}")

        # 使用正则表达式匹配 8位日期_6位时间 格式
        pattern = re.compile(r"^\d{8}_\d{6}$")
        dirs = [
            d for d in self.base_dir.iterdir() 
            if d.is_dir() and pattern.match(d.name)
        ]
        
        if not dirs:
            raise FileNotFoundError(f"在 {self.base_dir} 中未找到时间戳目录")
            
        # 按目录名降序排列（时间戳越大表示越新）
        dirs.sort(key=lambda d: d.name, reverse=True)
        return dirs[0]
    def collect_results(self) -> dict:
        """执行完整结果收集"""
        self._validate_dirs()
        
        # 结果处理三部分
        metrics = self._process_results()
        summary_data = self._parse_summary()
        prediction_files = self._collect_predictions()
        
        # 数据库存储
        self._save_to_db(metrics, summary_data, prediction_files)
        
        # 打包所有结果
        archive_path = self._create_full_archive()
        
        return {
            "metrics": metrics,
            "summary": summary_data,
            "prediction_files": prediction_files,
            "archive_path": str(archive_path),
            "directory_structure": self._get_directory_tree()
        }

    def _process_results(self) -> Dict[str, dict]:
        """处理results目录下的嵌套JSON文件"""
        metrics = {}
        # 遍历所有模型子目录
        for model_dir in self.results_dir.iterdir():
            if model_dir.is_dir():
                model_name = model_dir.name
                metrics[model_name] = {}
                # 遍历数据集文件
                for result_file in model_dir.glob("*.json"):
                    dataset_name = result_file.stem
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        metrics[model_name][dataset_name] = {
                            'accuracy': data.get('accuracy', 0.0),
                            'file_path': str(result_file.relative_to(self.timestamp_dir))
                        }
        return metrics

    def _parse_summary(self) -> List[Dict]:
        """解析summary目录的所有文件"""
        summary_data = []
        for summary_file in self.summary_dir.iterdir():
            if summary_file.is_file():
                file_type = summary_file.suffix.lower()
                if file_type == '.csv':
                    summary_data.extend(self._parse_csv(summary_file))
                # elif file_type == '.md':
                #     summary_data.extend(self._parse_markdown(summary_file))
                # 可扩展其他文件类型解析
        return summary_data

    def _parse_markdown(self, md_file: Path) -> List[Dict]:
        """解析Markdown表格"""
        results = []
        with open(md_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        header = None
        for line in lines:
            if line.startswith('|'):
                parts = [p.strip() for p in line.split('|') if p.strip()]
                if not header:
                    header = parts
                else:
                    if len(parts) == len(header):
                        results.append(dict(zip(header, parts)))
        return results

    def _parse_csv(self, csv_file: Path) -> List[Dict]:
        """解析CSV文件"""
        import csv
        results = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(dict(row))
        return results

    def _collect_predictions(self) -> Dict[str, list]:
        """收集predictions目录结构信息"""
        predictions = {}
        for model_dir in self.predictions_dir.iterdir():
            if model_dir.is_dir():
                model_name = model_dir.name
                predictions[model_name] = []
                for dataset_file in model_dir.glob("*.json"):
                    predictions[model_name].append({
                        "dataset": dataset_file.stem,
                        "path": str(dataset_file.relative_to(self.timestamp_dir))
                    })
        return predictions

    def _create_full_archive(self) -> Path:
        """创建保留完整目录结构的ZIP包"""
        archive_dir = self.base_dir / "full_results"
        if not archive_dir.exists():
            # 创建full_results目录
            archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"full_results_{self.eval_id}.zip"
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加整个时间戳目录
            for file_path in self.timestamp_dir.rglob('*'):
                if file_path.is_file():
                    zipf.write(
                        file_path,
                        arcname=file_path.relative_to(self.base_dir.parent)
                    )
        return archive_path
    def _save_to_db(self, metrics: Dict[str, dict], summary_data: List[Dict], prediction_files: Dict[str, list]):
        """使用上下文管理器自动处理session"""

        with SessionLocal() as session:
            try:
                eval_record = session.get(Evaluation, self.eval_id)
                if eval_record:
                    # 合并所有结果数据
                    full_results = {
                        'metrics': metrics,
                        'summary': summary_data,
                        'prediction_files': prediction_files,
                        'archive_path': str(self._create_full_archive())
                    }
                    
                    # 使用merge方法确保对象状态正确
                    merged_record = session.merge(eval_record)
                    merged_record.results = full_results
                    session.commit()
            except Exception as e:
                session.rollback()
                raise RuntimeError(f"数据库更新失败: {str(e)}")

    def _validate_dirs(self):
        """验证所有必要目录"""
        required_dirs = [
            self.base_dir,
            self.timestamp_dir,
            self.results_dir,
            self.summary_dir,
            self.predictions_dir
        ]
        for d in required_dirs:
            if not d.exists():
                raise FileNotFoundError(f"缺失必要目录: {d}")
            
    def _get_directory_tree(self) -> dict:
        """生成目录树结构"""
        def _walk_dir(path: Path):
            return {
                "name": path.name,
                "type": "directory" if path.is_dir() else "file",
                "size": path.stat().st_size if path.is_file() else 0,
                "children": [_walk_dir(p) for p in path.iterdir()] if path.is_dir() else []
            }
        return _walk_dir(self.timestamp_dir)