import os
from typing import Optional

class Settings:
    # Telegram
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_WEBHOOK_URL: Optional[str] = os.getenv("TELEGRAM_WEBHOOK_URL")
    
    # Bot
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "instagram_manager_bot")
    
    # Admin
    ADMIN_TELEGRAM_ID: int = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Instagram Sessions
    SESSIONS_DIR: str = os.getenv("SESSIONS_DIR", "./sessions")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///instagram_manager.db"
    )
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # Server
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 3600
    
    # API Keys
    API_KEY: str = os.getenv("API_KEY", "")
    
    def __post_init__(self):
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        if not self.ADMIN_TELEGRAM_ID:
            raise ValueError("ADMIN_TELEGRAM_ID environment variable is required")
