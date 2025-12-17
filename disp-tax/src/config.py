"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Bot
    BOT_TOKEN: str = ""
    
    # Telegram API (for Telethon)
    API_ID: int = 0
    API_HASH: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./dispatcher.db"
    
    # Admin IDs (comma-separated)
    ADMIN_IDS: str = ""
    
    # Session storage
    SESSIONS_DIR: str = "./sessions"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/dispatcher.log"
    
    # Speech Recognition
    OPENAI_API_KEY: str = ""  # OpenAI API key for Whisper
    YANDEX_API_KEY: str = ""  # Yandex SpeechKit API key or IAM token
    YANDEX_IAM_TOKEN: str = ""  # Yandex IAM token (alternative to API key)
    SPEECH_PROVIDER: str = "auto"  # openai, yandex, or auto
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Parse admin IDs from comma-separated string."""
        if not self.ADMIN_IDS:
            return []
        return [int(uid.strip()) for uid in self.ADMIN_IDS.split(",") if uid.strip()]


settings = Settings()

