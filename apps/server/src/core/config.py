from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import MySQLDsn, RedisDsn, computed_field
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

class Settings(BaseSettings):
    # 基础配置
    APP_NAME: str = "AI Eval System"
    PROJECT_NAME: str = "AI Eval System"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 服务器配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000

    # 路径配置
    opencompass_path: Path = Path(
        os.getenv("OPENCOMPASS_PATH", BASE_DIR / "libs" / "OpenCompass"))
    workspace: Path = Path(
        os.getenv("WORKING_DIR", BASE_DIR / "workspace"))
    logs_dir: Path = workspace / "logs" / "celery_task"

    # 数据库配置（分项模式）
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = os.getenv("MYSQL_PORT", 3306)
    mysql_user: str = os.getenv("MYSQL_USER", "ai_eval_user")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "ai_eval_password")
    mysql_db: str = os.getenv("MYSQL_DB", "ai_eval")
    
    # 调试模式
    mysql_debug: bool = False
    
    # 安全配置
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: str = "your-secret-key-here"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30 # 30天


    # CORS配置
    CORS_ORIGINS: list = [
        "http://localhost:3000",    # 前端开发地址
    ]

    # Redis配置
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery配置
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    # Dify2OpenAI服务
    dify2openai_url: str = os.getenv("DIFY2OPENAI_URL", "http://localhost:3099/v1/")

    # 并发配置
    celery_concurrency: int = os.getenv("CELERY_CONCURRENCY", 1)


    # 头像相关配置
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", workspace / "data" / "user_uploads"))
    avatar_storage_dir: Path = Path(os.getenv("AVATAR_DIR", upload_dir / "avatars"))
    avatar_url_prefix: str = "/api/uploads/avatars"  # API URL前缀
    default_avatar_url: str = "/images/default-avatar.png"  # 前端静态资源
    max_avatar_size: int = 2 * 1024 * 1024  # 2MB
    allowed_avatar_types: list = ["image/jpeg", "image/png", "image/gif", "image/webp"]

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
            scheme="mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            path=self.mysql_db,
            query="charset=utf8mb4"  # 移除非标准参数
        )


settings = Settings()

# 在 config.py 末尾添加验证
if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"OpenCompass路径是否存在: {(BASE_DIR / 'libs' / 'OpenCompass').exists()}")
    print(f"数据库连接URL: {settings.db_url.unicode_string()}")
    print(f"Dify2OpenAI URL: {settings.dify2openai_url}")
