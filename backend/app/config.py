"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # LLM Provider: "auto", "anthropic" (API key), "bedrock" (AWS), or "gemini" (Google)
    llm_provider: str = "auto"

    # Anthropic API (direct)
    anthropic_api_key: str = ""
    anthropic_model_id: str = "claude-sonnet-4-20250514"

    # AWS Bedrock (alternative)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"
    bedrock_model_id: str = "amazon.nova-lite-v1:0"
    
    # Google Gemini
    gemini_api_key: str = ""
    # "gemini-2.5-flash" or "gemini-1.5-flash" are fast and cheap
    gemini_model_id: str = "gemini-2.5-flash"

    # CORS
    frontend_url: str = "http://localhost:5173"
    cors_allow_origins: str = ""
    cors_allow_origin_regex: str = ""

    # Scraping
    scraping_delay_min: float = 1.0
    scraping_delay_max: float = 3.0
    scraping_max_products: int = 15

    # Agent thresholds
    conviction_threshold: float = 0.80
    max_socratic_turns: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def get_cors_allow_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)

        if not origins:
            origins = ["http://localhost:5173", "http://localhost:3000"]

        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()
