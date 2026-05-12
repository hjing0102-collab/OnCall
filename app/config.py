"""配置管理模块"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "SuperOnCallAgent"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 9900

    dashscope_api_key: str = ""
    dashscope_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen-max"
    dashscope_embedding_model: str = "text-embedding-v4"

    rag_top_k: int = 3
    chunk_max_size: int = 800
    chunk_overlap: int = 100


config = Settings()
