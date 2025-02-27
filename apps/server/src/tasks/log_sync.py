"""
日志同步任务
将日志文件同步到Redis缓存
"""

import os
import time
import threading
import logging
from pathlib import Path
from typing import Dict, Set, Optional
from apps.server.src.utils.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class LogSyncManager:
    """日志同步管理器
    在后台线程中运行，定期将新的日志文件行同步到Redis
    """
    
    def __init__(self, sync_interval: int = 5):
        """初始化日志同步管理器
        
        Args:
            sync_interval: 同步间隔（秒），默认5秒
        """
        self.sync_interval = sync_interval
        self.running = False
        self.thread = None
        self.file_positions: Dict[str, Dict] = {}  # 记录文件位置
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
        self.logs_dir = os.path.join(self.BASE_DIR, "logs", "opencompass")
        
    def start(self):
        """启动日志同步线程"""
        if self.thread and self.thread.is_alive():
            logger.warning("日志同步线程已经在运行")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()
        logger.info("日志同步线程已启动")
        
    def stop(self):
        """停止日志同步线程"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
            logger.info("日志同步线程已停止")
    
    def _sync_loop(self):
        """同步循环"""
        while self.running:
            try:
                self._sync_all_logs()
            except Exception as e:
                logger.error(f"同步日志时出错: {str(e)}")
                
            # 等待下一次同步
            time.sleep(self.sync_interval)
    
    def _sync_all_logs(self):
        """同步所有日志文件"""
        # 确保日志目录存在
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # 查找所有日志文件
        log_files = list(Path(self.logs_dir).glob("eval_*_*.log"))
        
        for log_file in log_files:
            try:
                self._sync_file(str(log_file))
            except Exception as e:
                logger.error(f"同步文件 {log_file} 时出错: {str(e)}")
    
    def _sync_file(self, file_path: str):
        """同步单个文件
        
        Args:
            file_path: 文件路径
        """
        # 从文件名中提取任务ID
        try:
            file_name = os.path.basename(file_path)
            task_id = int(file_name.split('_')[1])
        except (ValueError, IndexError):
            logger.warning(f"无法从文件名 {file_path} 中提取任务ID")
            return
        
        # 检查文件是否已经被追踪
        if file_path not in self.file_positions:
            self.file_positions[file_path] = {
                "position": 0,
                "last_modified": 0,
                "task_id": task_id
            }
        
        # 获取文件信息
        try:
            file_stat = os.stat(file_path)
            # 如果文件大小比上次同步时小，说明文件被重新创建，重置位置
            if file_stat.st_size < self.file_positions[file_path]["position"]:
                self.file_positions[file_path]["position"] = 0
                
            # 如果文件没有变化，跳过
            if (file_stat.st_mtime <= self.file_positions[file_path]["last_modified"] and
                file_stat.st_size <= self.file_positions[file_path]["position"]):
                return
                
            # 更新最后修改时间
            self.file_positions[file_path]["last_modified"] = file_stat.st_mtime
            
            # 读取新的行
            with open(file_path, 'r') as f:
                f.seek(self.file_positions[file_path]["position"])
                new_lines = f.readlines()
                
                # 更新位置
                self.file_positions[file_path]["position"] = f.tell()
                
            # 将新的行添加到Redis
            if new_lines:
                for line in new_lines:
                    line = line.rstrip('\n')
                    if line:  # 忽略空行
                        RedisManager.append_log(task_id, line)
                
                logger.debug(f"已同步 {len(new_lines)} 行到任务 {task_id}")
                
        except FileNotFoundError:
            # 文件可能被删除
            if file_path in self.file_positions:
                del self.file_positions[file_path]
        except Exception as e:
            logger.error(f"同步文件 {file_path} 失败: {str(e)}")

# 全局单例
log_sync_manager = LogSyncManager()

def start_log_sync():
    """启动日志同步服务"""
    log_sync_manager.start()

def stop_log_sync():
    """停止日志同步服务"""
    log_sync_manager.stop() 