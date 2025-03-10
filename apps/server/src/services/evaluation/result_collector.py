from pathlib import Path
import tarfile
import json
import os
class ResultCollector:
    def __init__(self, eval_id: int, work_dir: Path):
        """
        Args:
            eval_id: 评估任务ID
            work_dir: OpenCompass输出目录（eval_{eval_id}）
        """
        self.eval_id = eval_id
        self.work_dir = work_dir
        self.results_dir = os.path.join(work_dir, "results")
        self.summary_dir = os.path.join(work_dir, "summary")
        
    def collect_results(self) -> dict:
        """执行结果收集"""
        print(f"开始收集结果: {self.eval_id}")
        return
        self._validate_dirs()
        metrics = self._parse_metrics()
        log_archive = self._archive_logs()
        return {
            "metrics": metrics,
            "log_archive": log_archive,
            "work_dir": str(self.work_dir)
        }
    
    def _validate_dirs(self):
        """验证目录结构"""
        if not self.work_dir.exists():
            raise FileNotFoundError(f"工作目录不存在: {self.work_dir}")
            
        required_dirs = [self.results_dir, self.summary_dir]
        for d in required_dirs:
            if not d.exists():
                raise FileNotFoundError(f"缺失必要目录: {d}")

    def _parse_metrics(self) -> dict:
        """从outputs目录解析评估结果"""
        result_files = list(self.results_dir.glob("*.json"))
        if not result_files:
            raise ValueError("未找到结果文件")
            
        # 以最新结果文件为准
        latest_file = max(result_files, key=lambda f: f.stat().st_mtime)
        with open(latest_file) as f:
            return json.load(f)
    
    def _archive_logs(self) -> Path:
        """打包日志目录"""
        archive_path = self.work_dir / "logs.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(self.work_dir, arcname="logs")
        return archive_path 