from utils.redis_manager import RedisManager

class LogHandler:
    def __init__(self, eval_id: int):
        self.eval_id = eval_id
    
    def process_line(self, raw_line: str):
        """处理单行日志"""
        # 基础清洗
        cleaned_line = raw_line.strip()
        if not cleaned_line:
            return
        
        # 实时发布
        RedisManager.append_log(self.eval_id, cleaned_line)
    
