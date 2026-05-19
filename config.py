"""Configuración de SpringAgent desde variables de entorno."""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de la aplicación leídos de `.env` y del entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "SpringAgent"
    app_version: str = "1.0.0"
    app_port: int = 8001
    app_env: str = "development"
    log_level: str = "INFO"

    # Security
    service_api_key: str = "springagent-secure-key-change-in-production"

    # CORS
    cors_origins: str = "http://localhost:3005,http://localhost:3000"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: int = 120
    ollama_num_ctx: int = 4096

    # NestJS
    nestjs_base_url: str = "http://localhost:3005/api"
    nestjs_service_key: str = "springagent-internal-key-change-in-production"
    nestjs_timeout: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_ttl_cache: int = 300
    redis_ttl_conversation: int = 1800

    # OCR
    ocr_lazy_load: bool = False
    ocr_max_upload_size: int = 10485760

    # Limits
    max_conversation_history: int = 10
    max_tool_retries: int = 1
    rate_limit_per_minute: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        """Lista de orígenes CORS permitidos."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
