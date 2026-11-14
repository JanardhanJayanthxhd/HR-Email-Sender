from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Telegram
    telegram_bot_token: str
    allowed_user_id: int

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:4b-instruct-2507-q4_K_M"
    llm_temperature: float = 0.0

    # Ollama-specific
    ollama_base_url: str = "http://localhost:11434"
    ollama_num_ctx: int = 8192

    # Gmail
    gmail_address: str
    gmail_app_password: str
    reply_to_email: str
    sender_name: str

    # Application behavior
    daily_send_cap: int = 15
    send_delay_min: int = 30
    send_delay_max: int = 60

    # Paths
    resume_dir: Path = Path("resume")
    database_path: Path = Path("data/applications.db")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
