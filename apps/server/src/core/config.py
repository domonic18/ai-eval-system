from pydantic_settings import BaseSettings
from pathlib import Path
import os

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

class Settings(BaseSettings):
    """系统配置类，用于管理所有配置项
    
    使用pydantic_settings来支持环境变量和.env文件的自动加载
    所有配置项都可以通过环境变量覆盖
    """
    # 基本信息
    app_name: str = "AI Evaluation System"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = True
    
    # 路径配置
    base_dir: Path = BASE_DIR
    opencompass_path: Path = BASE_DIR / "libs" / "OpenCompass"
    
    # 数据库配置
    db_url: str = os.getenv(
        "DB_URL", 
        "mysql+pymysql://root:password@localhost:3306/ai_eval?charset=utf8mb4"
    )
    
    # MySQL配置
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "password")
    mysql_db: str = os.getenv("MYSQL_DB", "ai_eval")
    
    # Redis配置
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Celery配置
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", redis_url)
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", redis_url)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        
    @property
    def mysql_connection_string(self) -> str:
        """生成MySQL连接字符串"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"

# 创建全局配置实例
settings = Settings()

# 导出常用配置常量
APP_NAME = settings.app_name
API_PREFIX = settings.api_prefix
DEBUG = settings.debug
OPENCOMPASS_PATH = str(settings.opencompass_path)
DB_URL = settings.mysql_connection_string  # 使用MySQL连接字符串
REDIS_URL = settings.redis_url 