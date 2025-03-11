#!/usr/bin/env python3
# OpenCompass评测任务执行器

import os
import subprocess
import time
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from utils.redis_manager import RedisManager
from datetime import datetime
from utils.log_handler import LogHandler
from pathlib import Path

logger = logging.getLogger(__name__)


class RunnerBase:
    """任务执行器基础类"""
    
    def __init__(self, 
                eval_id: Optional[int] = None,
                working_dir: str = None, 
                log_buffer_size: int = 1000,
                opencompass_path: str = None):
        """初始化
        
        Args:
            task_id: 任务ID，用于Redis日志存储
            working_dir: 工作目录，默认使用当前目录
            log_buffer_size: 日志缓冲区大小
            opencompass_path: OpenCompass安装路径
        """
        # 设置任务ID
        self.eval_id = eval_id
        # 设置工作目录
        self.working_dir = working_dir or os.getcwd()
        # 设置结果目录（专属工作目录，用来存放opencompass的输出结果）
        self.workspace_dir = self._prepare_workspace_dir()
        # 日志缓冲区
        self.log_buffer = []
        self.log_buffer_size = log_buffer_size
        # 当前进程
        self.process = None
        # 设置OpenCompass路径
        self.opencompass_path = opencompass_path
        # 日志文件
        self.log_file_path = None
        self.log_file = None
        # 运行状态
        self.is_running = False
        self.is_finished = False
        self.return_code = None

        self.start_time = None
        self.end_time = None
        self.log_handler = LogHandler(self.eval_id)  # 新增
    def terminate(self) -> bool:
        """终止进程"""
        import psutil
        if self.process:
            parent = psutil.Process(self.process.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
    @property
    def pid(self) -> Optional[int]:
        """获取进程ID"""
        return self.process.pid if self.process else None
    
    def get_raw_logs(self) -> List[str]:
        """获取原始日志（不包含状态信息）"""
        return self.log_buffer.copy()

    def _update_status(self, status: str):
        """更新状态
        Args:
            status: running or finished or failed
        """

        if status == "running":
            # 1. 更新为运行中
            self.is_running = True
            if self.eval_id is not None:
                status_data = {
                    "is_running": self.is_running,
                    "timestamp": time.time()
                }
                RedisManager.update_task_status(self.eval_id, status_data)
        elif status == "finished":
            # 2. 更新为已完成
            self.is_running = False
            self.is_finished = True
            if self.eval_id is not None:
                status_data = {
                    "status": "finished",
                    "return_code": self.return_code,
                    "is_successful": self.return_code == 0,
                    "timestamp": time.time()
                }
                RedisManager.update_task_status(self.eval_id, status_data)
        elif status == "failed":
            self.is_running = False
            self.is_finished = True
            if self.eval_id is not None:
                status_data = {
                    "status": "failed",
                    "return_code": self.return_code,
                    "is_successful": False,
                    "timestamp": time.time()
                }
                RedisManager.update_task_status(self.eval_id, status_data)
    def _setup_log_file(self, log_file_path: str) -> bool:
        """设置日志文件
        
        创建日志文件目录并打开日志文件
        
        Args:
            log_file_path: 日志文件路径
            
        Returns:
            bool: 是否成功设置
        """
        try:
            self.log_file_path = log_file_path
            self.log_file = None
            
            if not log_file_path:
                return True
                
            # 创建日志文件目录
            log_dir = os.path.dirname(log_file_path)
            os.makedirs(log_dir, exist_ok=True)
            
            # 打开日志文件
            self.log_file = open(log_file_path, 'w', encoding='utf-8')
            print(f"OpenCompass输出将记录到: {log_file_path}")
            return True
        except Exception as e:
            print(f"设置日志文件时出错: {str(e)}")
            self.log_file_path = None
            self.log_file = None
            return False


        """仅保留基础日志缓冲"""
        # 移除Redis相关代码
        if len(self.log_buffer) >= self.log_buffer_size:
            self.log_buffer.pop(0)
        self.log_buffer.append(line)
    def _close_log_file(self) -> None:
        """安全地关闭日志文件"""
        if self.log_file:
            try:
                self.log_file.close()
            except Exception as e:
                print(f"关闭日志文件时出错: {str(e)}")
            finally:
                self.log_file = None
    def _update_log(self, line: str):
        """仅保留基础日志缓冲"""
        # 移除Redis相关代码
        if len(self.log_buffer) >= self.log_buffer_size:
            self.log_buffer.pop(0)
        self.log_buffer.append(line)

        # 写入日志文件
        if self.log_file:
            try:
                self.log_file.write(line)
                self.log_file.flush()
            except Exception as e:
                print(f"写入日志文件时出错: {str(e)}")

    def _prepare_workspace_dir(self) -> Path:
        """准备专属工作目录"""
        if not self.eval_id:
            return self.working_dir / "temp"
            
        work_dir = os.path.join(self.working_dir, f"eval_{self.eval_id}")
        # work_dir = self.working_dir / f"eval_{self.eval_id}"
        os.makedirs(work_dir, exist_ok=True)
        return work_dir

    def build_command(self, *args, **kwargs) -> str:
        """抽象基类，定义公共接口"""
        raise NotImplementedError("子类必须实现build_command方法")
    
    def run_sync(self, command: str ) -> int:
        """同步执行命令并实时处理输出"""
        self.start_time = datetime.now()
        try:
            print(f"执行命令: {command}")
            self.process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # 1. 更新为运行中
            self._update_status("running")
            # 2. 设置日志文件
            self._setup_log_file(self.log_file_path)
        
            # 3. 实时处理输出
            while self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                # 4. 清洗日志
                cleaned_line = line.strip()
                # 5. 处理日志
                self.log_handler.process_line(cleaned_line) 

                # 6. 更新日志缓冲
                self._update_log(cleaned_line)
                print(f"OpenCompass输出: {cleaned_line}")

            # 7. 获取返回码
            self.return_code = self.process.poll()
            print(f"进程已结束，返回码: {self.return_code}")
            
            # 8. 更新状态为已完成
            self._update_status("finished")
            
            return self.return_code
        except Exception as e:
            error_msg = f"监控进程输出时出错: {str(e)}"
            print(error_msg)
            self._update_status("failed")
            return -1


# 单例模式，保存正在运行的任务
_runners = {}

def get_runner(eval_id: str) -> Optional[RunnerBase]:
    """获取指定任务ID的运行器
    
    Args:
        task_id: 任务ID
        
    Returns:
        Optional[OpenCompassRunner]: 运行器实例，不存在则返回None
    """
    return _runners.get(eval_id)

def create_runner(eval_id: str, working_dir: str = None, opencompass_path: str = None) -> RunnerBase:
    """创建任务运行器
    
    Args:
        task_id: 任务ID
        working_dir: 工作目录
        opencompass_path: OpenCompass路径
        
    Returns:
        OpenCompassRunner: 新创建的运行器实例
    """
    # 支持上下文管理器模式
    runner = RunnerBase(eval_id=eval_id, working_dir=working_dir, opencompass_path=opencompass_path)
    _runners[eval_id] = runner
    return runner

def remove_runner(eval_id: str) -> bool:
    """移除任务运行器
    
    Args:
        task_id: 任务ID
        
    Returns:
        bool: 是否成功移除
    """
    if eval_id in _runners:
        runner = _runners[eval_id]
        # 如果任务正在运行，先终止
        if runner.is_running:
            runner.terminate()

        # 移除任务
        del _runners[eval_id]
        return True
    return False
