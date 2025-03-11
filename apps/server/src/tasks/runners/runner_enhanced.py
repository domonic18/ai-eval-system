from utils.redis_manager import RedisManager
from tasks.runners.runner_base import RunnerBase
from tasks.runners.env_manager import EnvManager
from services.evaluation.result_collector import ResultCollector
from schemas.eval import EvaluationCreate

class EnhancedRunner(RunnerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env_manager = EnvManager(self.eval_id)     # 新增环境管理模块

    def execute(self, eval_data: EvaluationCreate):
        """增强的执行流程"""
        try:
            # 1. 配置环境变量
            self.env_manager.load_env_json(eval_data.env_vars)

            # 2. 环境变量注入
            full_cmd = self._build_command(eval_data)
            
            # 3. 执行原始命令
            exit_code = super().run_sync(full_cmd)
            
            return exit_code
        except Exception as e:
            self._handle_error(e)
            raise e
            
    def _build_command(self, eval_data: EvaluationCreate) -> str:
        """根据配置构建命令"""
        
        # 数据集处理 - 确保是正确的列表格式
        datasets = eval_data.dataset_names
        
        # 如果是字符串（JSON），尝试解析为Python列表
        if isinstance(datasets, str):
            try:
                import json
                datasets = json.loads(datasets)
            except:
                # 如果解析失败，确保至少有一个有效的数据集名称
                datasets = [datasets.strip('"[]')]
        
        # 将数据集列表合并为空格分隔的字符串
        datasets_str = " ".join(datasets) if isinstance(datasets, list) else str(datasets)
        
        cmd = [
            "opencompass",
            f"--models {eval_data.model_name}",
            f"--datasets {datasets_str}",
            f"--work-dir {self.output_dir}",
            f"--debug"
        ]

        # 添加可选参数
        # if eval_data.eval_config:
        #     for key, value in eval_data.eval_config.items():
        #         if value:
        #             cmd.append(f"--{key} {value}")

        return self.env_manager.inject_to_command(" ".join(cmd))
    def _handle_error(self, error: Exception):
        """统一错误处理"""
        self._update_status("failed")