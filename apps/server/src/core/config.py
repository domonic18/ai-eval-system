from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import MySQLDsn, RedisDsn, computed_field
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


class Settings(BaseSettings):
    # 基础配置
    PROJECT_NAME: str = "AI Eval System"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 服务器配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # 路径配置
    opencompass_path: Path = BASE_DIR / "libs" / "OpenCompass"
    
    # 数据库配置（分项模式）
    mysql_host: str = os.getenv("MYSQL_HOST")
    mysql_port: int = os.getenv("MYSQL_PORT")
    mysql_user: str = os.getenv("MYSQL_USER")
    mysql_password: str = os.getenv("MYSQL_PASSWORD")
    mysql_db: str = os.getenv("MYSQL_DB")
    
    # 调试模式
    mysql_debug: bool = True
    
    # 安全配置
    JWT_SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # CORS配置
    CORS_ORIGINS: list = [
        "http://localhost:3000",    # 前端开发地址
        "https://your-domain.com"   # 生产环境域名
    ]

    # Redis配置
    redis_url: RedisDsn = "redis://localhost:6379/0"  # 使用RedisDsn类型验证
    
    # Celery配置
    celery_broker_url: RedisDsn = "redis://localhost:6379/0"
    celery_result_backend: RedisDsn = "redis://localhost:6379/1"  # 建议与broker使用不同DB

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AI_EVAL_",  # 添加环境变量前缀避免冲突
        env_nested_delimiter="__",
        extra="ignore"
    )
    
    @computed_field
    @property
    def db_url(self) -> MySQLDsn:
        return MySQLDsn.build(
            scheme="mysql+asyncmy",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            path=self.mysql_db,
        )

settings = Settings()

# 在 config.py 末尾添加验证
if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"OpenCompass路径是否存在: {(BASE_DIR / 'libs' / 'OpenCompass').exists()}")
