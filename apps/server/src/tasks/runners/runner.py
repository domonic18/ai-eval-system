#!/usr/bin/env python3
# OpenCompass评测任务执行器

import os
import sys
import subprocess
import time
import json
import signal
import tempfile
import threading
from pathlib import Path
from threading import Thread, Event
from typing import Dict, Any, Optional, List, Tuple, Callable
from utils.redis_manager import RedisManager
from datetime import datetime

class OpenCompassRunner:
    """OpenCompass评测任务执行器"""
    
    def __init__(self, 
                task_id: Optional[int] = None,
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
        self.task_id = task_id
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
        self.log_file = None
        # 运行状态
        self.is_running = False
        self.is_finished = False
        self.return_code = None
        # 监控线程
        self.monitor_thread = None
        # 停止信号
        self._stop_event = Event()
        # 状态回调函数列表
        self.status_callbacks = []
        # PID文件
        self.pid_file = None
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """支持上下文管理器模式"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出时自动清理资源"""
        self.terminate()
        self._close_log_file()
        self.join_monitor_thread(timeout=5)
        return False  # 不抑制异常
    
    def register_status_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注册状态变更回调函数
        
        Args:
            callback: 回调函数，接收状态字典作为参数
        """
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable):
        """取消注册状态回调函数
        
        Args:
            callback: 之前注册的回调函数
        """
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    def _notify_status_change(self, status: Dict[str, Any]):
        """通知所有回调函数状态已变更
        
        Args:
            status: 当前状态字典
        """
        for callback in self.status_callbacks[:]:  # 复制列表以防回调中修改
            try:
                callback(status)
            except Exception as e:
                print(f"执行状态回调时出错: {str(e)}")
    
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

        cmd_parts.append(f"--debug")
        
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
        
        # 更新状态消息
        if "status" in line.lower() or "stage" in line.lower():
            old_message = self.status_message
            self.status_message = line.strip()
            
            # 如果状态消息变更，通知回调
            if old_message != self.status_message:
                self._notify_status_change(self.get_status())
    
    def _monitor_output(self):
        """监控进程输出并记录日志"""
        print(f"开始监控进程输出...")
        try:
            while not self._stop_event.is_set() and self.process.poll() is None:  # 进程还在运行
                # 读取输出
                line = self.process.stdout.readline()
                if not line:
                    break
                
                # 由于subprocess.Popen已经设置了text=True，line已经是字符串
                line_str = line.strip()
                
                # 保存到缓冲区
                self._update_log(line_str)
                
                # 写入日志文件
                self._write_to_log_file(line_str + '\n')

                # 打印工作日志
                print(f"OpenCompass输出: {line_str}")
            
            # 处理剩余输出
            for line in self.process.stdout:
                # 由于subprocess.Popen已经设置了text=True，line已经是字符串
                line_str = line.strip()
                self._update_log(line_str)
                self._write_to_log_file(line_str + '\n')
            
            # 获取返回码
            self.return_code = self.process.poll()
            print(f"进程已结束，返回码: {self.return_code}")
            
            # 关闭日志文件
            self._close_log_file()
            
            # 更新状态
            old_running = self.is_running
            old_finished = self.is_finished
            
            self.is_running = False
            self.is_finished = True
            
            # 如果状态发生变化，通知回调
            if old_running != self.is_running or old_finished != self.is_finished:
                self._notify_status_change(self.get_status())
            
            # 更新Redis状态
            if self.task_id is not None:
                status_data = {
                    "status": "finished",
                    "return_code": self.return_code,
                    "is_successful": self.return_code == 0,
                    "timestamp": time.time()
                }
                RedisManager.update_task_status(self.task_id, status_data)
                self._notify_status_change(status_data)
                
        except Exception as e:
            error_msg = f"监控进程输出时出错: {str(e)}"
            print(error_msg)
            self._update_log(error_msg)
            
            # 确保状态被更新
            old_running = self.is_running
            old_finished = self.is_finished
            
            self.is_running = False
            self.is_finished = True
            self.return_code = self.process.poll() or -1
            
            # 如果状态发生变化，通知回调
            if old_running != self.is_running or old_finished != self.is_finished:
                self._notify_status_change(self.get_status())
            
            # 确保日志文件被关闭并记录错误
            if self.log_file:
                self._write_to_log_file(f"{error_msg}\n")
                self._close_log_file()
    
    def join_monitor_thread(self, timeout=None):
        """等待监控线程完成
        
        Args:
            timeout: 等待超时时间(秒)，None表示一直等待
            
        Returns:
            bool: 线程是否已完成
        """
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout)
        return not (self.monitor_thread and self.monitor_thread.is_alive())
    
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
    
    def _close_log_file(self) -> None:
        """安全地关闭日志文件"""
        if self.log_file:
            try:
                self.log_file.close()
            except Exception as e:
                print(f"关闭日志文件时出错: {str(e)}")
            finally:
                self.log_file = None
                
    def _write_to_log_file(self, content: str) -> None:
        """写入内容到日志文件
        
        Args:
            content: 要写入的内容
        """
        if not self.log_file:
            return
            
        try:
            self.log_file.write(content)
            self.log_file.flush()
        except Exception as e:
            print(f"写入日志文件时出错: {str(e)}")
            self._close_log_file()
            
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
        
        # 重置停止信号
        self._stop_event.clear()
        
        # 设置日志文件
        if not self._setup_log_file(log_file_path):
            return False
        
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
            
            # 启动监控线程
            self.monitor_thread = Thread(target=self._monitor_output)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            # 将任务标记为运行状态
            old_running = self.is_running
            old_finished = self.is_finished
            
            self.is_running = True
            self.is_finished = False
            
            # 如果状态变更，通知回调
            if old_running != self.is_running or old_finished != self.is_finished:
                self._notify_status_change(self.get_status())
                
            print(f"任务已标记为运行状态，监控线程已启动")
            
            return True
        
        except Exception as e:
            print(f"执行命令时出错: {str(e)}")
            # 确保资源被清理
            self._close_log_file()
            return False
    
    def terminate(self) -> bool:
        """终止OpenCompass进程
        
        终止进程，并更新相关状态
        
        Returns:
            bool: 是否成功终止
        """
        if not self.is_running or not self.process:
            return False
        
        # 发送停止信号给监控线程
        self._stop_event.set()
                
        try:
            # 发送SIGTERM信号
            self.process.terminate()
            
            # 等待进程结束
            for _ in range(10):  # 最多等待10秒
                if self.process.poll() is not None:
                    termination_msg = "进程已通过SIGTERM信号终止"
                    self._update_log(termination_msg)
                    self._write_to_log_file(f"{termination_msg}\n")
                    # 更新状态
                    self.is_running = False
                    self.is_finished = True
                    self.status_message = termination_msg
                    return True
                time.sleep(1)
                
            # 如果进程仍在运行，发送SIGKILL信号
            self.process.kill()
            kill_msg = "进程已通过SIGKILL信号强制终止"
            self._update_log(kill_msg)
            self._write_to_log_file(f"{kill_msg}\n")
            # 更新状态
            self.is_running = False
            self.is_finished = True
            self.status_message = kill_msg
            return True
            
        except Exception as e:
            error_msg = f"终止进程时出错: {str(e)}"
            self._update_log(error_msg)
            self._write_to_log_file(f"{error_msg}\n")
            # 更新状态
            self.is_running = False
            self.is_finished = True
            self.status_message = error_msg
            return False
        finally:
            # 等待监控线程结束
            self.join_monitor_thread(timeout=5)
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        status = {
            "is_running": self.is_running,
            "is_finished": self.is_finished,
            "return_code": self.return_code,
            "progress": self.progress,
            "status_message": self.status_message,
            "recent_logs": self.get_recent_logs()
        }
        return status
    
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
    
    def get_results(self):
        """获取评估结果
        
        Returns:
            dict: 评估结果
        """
        if not self.is_finished:
            return {"error": "任务尚未完成"}
        
        if self.return_code != 0:
            return {"error": f"任务执行失败，返回码: {self.return_code}"}
        
        # 这里可以添加解析OpenCompass结果文件的逻辑
        # 简化实现，返回基本信息
        return {
            "status": "success" if self.return_code == 0 else "failed",
            "return_code": self.return_code,
            "logs": self.get_recent_logs(20)  # 返回最近20行日志
        }
    
    def get_error_message(self) -> str:
        """获取错误信息
        
        Returns:
            str: 错误信息
        """
        if not self.is_finished:
            return "任务尚未完成"
        
        if self.return_code == 0:
            return ""
        
        # 尝试从日志中提取错误信息
        error_logs = []
        for log in reversed(self.log_buffer):
            if "error" in log.lower() or "exception" in log.lower() or "failed" in log.lower():
                error_logs.append(log)
                if len(error_logs) >= 5:  # 最多收集5条错误日志
                    break
        
        if error_logs:
            return "\n".join(reversed(error_logs))
        else:
            return f"任务执行失败，返回码: {self.return_code}"
    
    @property
    def is_successful(self) -> bool:
        """判断任务是否成功完成
        
        Returns:
            bool: 是否成功完成
        """
        return self.is_finished and self.return_code == 0

    def add_log(self, log_line: str) -> None:
        """添加日志行
        
        Args:
            log_line: 日志行
        """
        # 添加到内存缓冲区
        self.log_buffer.append(log_line)
        if len(self.log_buffer) > self.log_buffer_size:
            # 超出缓冲区大小，删除旧日志
            self.log_buffer = self.log_buffer[-self.log_buffer_size:]
        
        # 如果有任务ID，则添加到Redis
        if self.task_id is not None:
            RedisManager.append_log(self.task_id, log_line)

    def update_status(self, progress: float = None, message: str = None) -> None:
        """更新状态信息
        
        Args:
            progress: 进度百分比(0-100)
            message: 状态信息
        """
        if progress is not None:
            self.progress = progress
        if message is not None:
            self.status_message = message
            
        # 添加状态更新到日志
        status_log = f"进度: {self.progress:.1f}%, 状态: {self.status_message}"
        self.add_log(status_log)
        
        # 如果有任务ID，则更新Redis中的任务状态
        if self.task_id is not None:
            status_data = {
                "progress": self.progress,
                "status_message": self.status_message,
                "timestamp": time.time()
            }
            RedisManager.update_task_status(self.task_id, status_data)

    def monitor_task(self):
        """改进的监控方法"""
        try:
            while self.is_running and not self.is_finished:
                # 添加更多状态检查
                if self.progress > 0:
                    self._update_progress()
                if self.status_message:
                    self._update_status()
                time.sleep(5)
                
            # 任务完成后的处理
            self._handle_task_completion()
            
        except Exception as e:
            self._handle_monitoring_error(e)

    def run_sync(self, command: str, log_file: str) -> int:
        """同步执行命令并实时处理输出"""
        self.start_time = datetime.now()
        try:
            self.process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        
            while not self._stop_event.is_set() and self.process.poll() is None:  # 进程还在运行
                # 读取输出
                line = self.process.stdout.readline()
                if not line:
                    break
                
                # 由于subprocess.Popen已经设置了text=True，line已经是字符串
                line_str = line.strip()
                
                # 保存到缓冲区
                self._update_log(line_str)
                
                # 写入日志文件
                self._write_to_log_file(line_str + '\n')

                # 打印工作日志
                print(f"OpenCompass输出: {line_str}")

            # 处理剩余输出
            for line in self.process.stdout:
                # 由于subprocess.Popen已经设置了text=True，line已经是字符串
                line_str = line.strip()
                self._update_log(line_str)
                self._write_to_log_file(line_str + '\n')
                
            # 获取返回码
            self.return_code = self.process.poll()
            print(f"进程已结束，返回码: {self.return_code}")
            
            # 关闭日志文件
            # self._close_log_file()

            # # 更新状态
            # old_running = self.is_running
            # old_finished = self.is_finished
            
            # self.is_running = False
            # self.is_finished = True
            # 更新Redis状态

            if self.task_id is not None:
                status_data = {
                    "status": "finished",
                    "return_code": self.return_code,
                    "is_successful": self.return_code == 0,
                    "timestamp": time.time()
                }
                RedisManager.update_task_status(self.task_id, status_data)
                # self._notify_status_change(status_data)
            return self.return_code
        except Exception as e:
            error_msg = f"监控进程输出时出错: {str(e)}"
            print(error_msg)
            self._update_log(error_msg)
            
            # # 确保状态被更新
            # old_running = self.is_running
            # old_finished = self.is_finished
            
            # self.is_running = False
            # self.is_finished = True
            # self.return_code = self.process.poll() or -1
            
            # # 如果状态发生变化，通知回调
            # if old_running != self.is_running or old_finished != self.is_finished:
            #     self._notify_status_change(self.get_status())
            
            # # 确保日志文件被关闭并记录错误
            # if self.log_file:
            #     self._write_to_log_file(f"{error_msg}\n")
            #     self._close_log_file()
            
        finally:
            self._close_log_file()
            self.end_time = datetime.now()
            self._finalize_task()

    def _finalize_task(self):
        """任务结束后的最终处理"""
        # 更新最终状态
        if self.task_id:
            status = {
                "status": "finished" if self.process.returncode == 0 else "failed",
                "exit_code": self.process.returncode,
                "end_time": self.end_time.isoformat(),
                "duration": (self.end_time - self.start_time).total_seconds()
            }
            RedisManager.update_task_status(self.task_id, status)
        
        # 关闭资源
        if self.process:
            self.process.stdout.close()

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
    # 支持上下文管理器模式
    runner = OpenCompassRunner(task_id=task_id, working_dir=working_dir, opencompass_path=opencompass_path)
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
            # 等待监控线程结束
            runner.join_monitor_thread(timeout=5)
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