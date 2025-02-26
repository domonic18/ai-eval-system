#!/usr/bin/env python3
# OpenCompass评测任务执行器

import os
import sys
import subprocess
import time
import json
import signal
import tempfile
from pathlib import Path
from threading import Thread
from typing import Dict, Any, Optional, List, Tuple

class OpenCompassRunner:
    """OpenCompass评测任务执行器"""
    
    def __init__(self, 
                working_dir: str = None, 
                log_buffer_size: int = 1000,
                opencompass_path: str = None):
        """初始化
        
        Args:
            working_dir: 工作目录，默认使用当前目录
            log_buffer_size: 日志缓冲区大小
            opencompass_path: OpenCompass安装路径
        """
        # 设置工作目录
        self.working_dir = working_dir or os.getcwd()
        # 日志缓冲区
        self.log_buffer = []
        self.log_buffer_size = log_buffer_size
        # 当前进程
        self.process = None
        # 进度信息
        self.progress = 0
        self.status_message = "未开始"
        # 设置OpenCompass路径
        self.opencompass_path = opencompass_path
        # 日志文件
        self.log_file_path = None
        # 运行状态
        self.is_running = False
        self.is_finished = False
        self.return_code = None
        # 监控线程
        self.monitor_thread = None
    
    def build_command(self, 
                     model_name: str, 
                     dataset_name: str, 
                     model_args: Dict[str, Any] = None,
                     dataset_args: Dict[str, Any] = None,
                     extra_args: List[str] = None) -> str:
        """构建OpenCompass命令
        
        Args:
            model_name: 模型名称
            dataset_name: 数据集名称
            model_args: 模型参数
            dataset_args: 数据集参数
            extra_args: 额外参数
            
        Returns:
            str: 构建好的命令
        """
        cmd_parts = ["opencompass"]
        
        # 添加模型参数
        cmd_parts.append(f"--models {model_name}")
        
        # 添加数据集参数
        cmd_parts.append(f"--datasets {dataset_name}")
        
        # 添加额外参数
        if extra_args:
            cmd_parts.extend(extra_args)
            
        # 合并命令
        command = " ".join(cmd_parts)
        print(f"构建的OpenCompass命令: {command}")
        return command
    
    def _update_log(self, line: str):
        """更新日志缓冲区
        
        Args:
            line: 日志行
        """
        # 限制缓冲区大小
        if len(self.log_buffer) >= self.log_buffer_size:
            self.log_buffer.pop(0)
        
        # 添加新日志
        self.log_buffer.append(line)
        
        # 尝试解析进度信息 - 这里需要根据OpenCompass的实际输出格式调整
        if "progress" in line.lower():
            try:
                # 示例格式: "Progress: 45%"
                progress_str = line.split("Progress:")[1].strip().rstrip("%")
                self.progress = float(progress_str)
            except (IndexError, ValueError):
                pass
            
        # 更新状态消息
        if "status" in line.lower() or "stage" in line.lower():
            self.status_message = line.strip()
    
    def _monitor_process(self):
        """监控进程输出"""
        for line in iter(self.process.stdout.readline, b''):
            if not line:
                break
                
            # 解码并处理日志行
            line_str = line.decode('utf-8', errors='replace').rstrip()
            self._update_log(line_str)
            
            # 如果有日志文件，写入
            if self.log_file_path:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"{line_str}\n")
        
        # 进程结束
        self.return_code = self.process.wait()
        self.is_running = False
        self.is_finished = True
        self._update_log(f"进程已结束，返回码: {self.return_code}")
    
    def run(self, command: str, log_file_path: str = None) -> bool:
        """执行命令
        
        Args:
            command: 要执行的命令
            log_file_path: 日志文件路径
            
        Returns:
            bool: 是否成功启动
        """
        # 如果已经在运行，则返回失败
        if self.is_running:
            print(f"任务已经在运行中")
            return False
        
        # 设置日志文件
        self.log_file_path = log_file_path
        log_file = None
        if log_file_path:
            # 创建日志文件目录
            log_dir = os.path.dirname(log_file_path)
            os.makedirs(log_dir, exist_ok=True)
            # 打开日志文件
            log_file = open(log_file_path, 'w')
            print(f"OpenCompass输出将记录到: {log_file_path}")
        
        # 设置命令
        # 假设是在Linux环境下，需要使用bash -c
        full_command = f"cd {self.opencompass_path} && {command}"
        print(f"正在执行命令: {full_command}")
        
        # 使用一个临时文件来记录进程ID，以便后续终止
        self.pid_file = tempfile.mktemp()
        
        try:
            # 创建新进程
            self.process = subprocess.Popen(
                full_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=self.working_dir
            )
            print(f"进程已启动，PID: {self.process.pid}")
            
            # 保存进程ID
            with open(self.pid_file, 'w') as f:
                f.write(str(self.process.pid))
            
            # 启动输出监控线程
            def monitor_output():
                """监控进程输出并记录日志"""
                print(f"开始监控进程输出...")
                while self.process.poll() is None:  # 进程还在运行
                    # 读取输出
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    
                    # 保存到缓冲区
                    self._update_log(line.strip())
                    
                    # 写入日志文件
                    if log_file:
                        log_file.write(line)
                        log_file.flush()
                    
                    # 检查进度信息 - 使用已有的方法而不是不存在的_parse_progress
                    self._update_log(line.strip())
                
                # 处理剩余输出
                for line in self.process.stdout:
                    self._update_log(line.strip())
                    if log_file:
                        log_file.write(line)
                        log_file.flush()
                
                # 获取返回码
                self.return_code = self.process.poll()
                print(f"进程已结束，返回码: {self.return_code}")
                
                # 关闭日志文件
                if log_file:
                    log_file.close()
                
                # 更新状态
                self.is_running = False
                self.is_finished = True
            
            # 启动监控线程
            self.monitor_thread = Thread(target=monitor_output)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            return True
        
        except Exception as e:
            print(f"执行命令时出错: {str(e)}")
            return False
    
    def terminate(self) -> bool:
        """终止OpenCompass进程
        
        Returns:
            bool: 是否成功终止
        """
        if not self.is_running or not self.process:
            return False
            
        try:
            # 发送SIGTERM信号
            self.process.terminate()
            
            # 等待进程结束
            for _ in range(10):  # 最多等待10秒
                if self.process.poll() is not None:
                    self._update_log("进程已通过SIGTERM信号终止")
                    return True
                time.sleep(1)
                
            # 如果进程仍在运行，发送SIGKILL信号
            self.process.kill()
            self._update_log("进程已通过SIGKILL信号强制终止")
            return True
            
        except Exception as e:
            self._update_log(f"终止进程时出错: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            "is_running": self.is_running,
            "is_finished": self.is_finished,
            "return_code": self.return_code,
            "progress": self.progress,
            "status_message": self.status_message,
            "recent_logs": self.get_recent_logs()
        }
    
    def get_recent_logs(self, lines: int = None) -> List[str]:
        """获取最近的日志
        
        Args:
            lines: 获取的行数，默认返回全部
            
        Returns:
            List[str]: 日志行列表
        """
        if lines is None or lines >= len(self.log_buffer):
            return self.log_buffer.copy()
        else:
            return self.log_buffer[-lines:]

# 单例模式，保存正在运行的任务
_runners = {}

def get_runner(task_id: str) -> Optional[OpenCompassRunner]:
    """获取指定任务ID的运行器
    
    Args:
        task_id: 任务ID
        
    Returns:
        Optional[OpenCompassRunner]: 运行器实例，不存在则返回None
    """
    return _runners.get(task_id)

def create_runner(task_id: str, working_dir: str = None, opencompass_path: str = None) -> OpenCompassRunner:
    """创建任务运行器
    
    Args:
        task_id: 任务ID
        working_dir: 工作目录
        opencompass_path: OpenCompass路径
        
    Returns:
        OpenCompassRunner: 新创建的运行器实例
    """
    runner = OpenCompassRunner(working_dir, opencompass_path=opencompass_path)
    _runners[task_id] = runner
    return runner

def remove_runner(task_id: str) -> bool:
    """移除任务运行器
    
    Args:
        task_id: 任务ID
        
    Returns:
        bool: 是否成功移除
    """
    if task_id in _runners:
        runner = _runners[task_id]
        # 如果任务正在运行，先终止
        if runner.is_running:
            runner.terminate()
        # 移除任务
        del _runners[task_id]
        return True
    return False

# 测试代码
if __name__ == "__main__":
    # 创建临时日志文件
    log_file = tempfile.mktemp(suffix=".log")
    
    # 创建运行器
    runner = OpenCompassRunner()
    
    # 构建命令 - 这里使用echo模拟OpenCompass输出
    cmd = 'for i in {1..10}; do echo "Progress: $i%"; sleep 1; done'
    
    # 运行命令
    runner.run(cmd, log_file)
    
    # 监控状态
    while runner.is_running or not runner.is_finished:
        status = runner.get_status()
        print(f"进度: {status['progress']}%, 状态: {status['status_message']}")
        time.sleep(2)
    
    # 打印结果
    print(f"命令执行完成，返回码: {runner.return_code}")
    print(f"日志文件: {log_file}") 