from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import MySQLDsn, RedisDsn, computed_field


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent.parent


class Settings(BaseSettings):
    
    # 路径配置
    opencompass_path: Path = BASE_DIR / "libs" / "OpenCompass"
    
    # 数据库配置（分项模式）
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "password"
    mysql_db: str = "ai_eval"
    
    # 调试模式
    mysql_debug: bool = True
    
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
