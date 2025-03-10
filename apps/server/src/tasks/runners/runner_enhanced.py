
from utils.redis_manager import RedisManager
from tasks.runners.runner_base import RunnerBase
from tasks.runners.env_manager import EnvManager
from services.evaluation.result_collector import ResultCollector
from schemas.eval import EvaluationCreate

class EnhancedRunner(RunnerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collector = ResultCollector(self.eval_id, self.workspace_dir)  # 新增结果收集模块
        self.env_manager = EnvManager(self.eval_id)     # 新增环境管理模块

    def execute(self, eval_data: EvaluationCreate):
        """增强的执行流程"""
        try:
            # 1. 环境变量注入
            # full_cmd = self.env_manager.inject_to_command(command)
            full_cmd = self._build_command(eval_data)
            
            # 2. 执行原始命令
            exit_code = super().run_sync(full_cmd)
            
            # 3. 结果收集
            if exit_code == 0:
                self.collector.collect_results()
            return exit_code
        except Exception as e:
            # pass
            self._handle_error(e)
            
    def _build_command(self, eval_data: EvaluationCreate) -> str:
        """根据配置构建命令"""
        cmd = [
            "opencompass",
            f"--models {eval_data.model_name}",
            f"--datasets {' '.join(eval_data.dataset_name)}",
            f"--work-dir {self.workspace_dir}",
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
        self.collector._archive_logs()  # 即使失败也保存日志